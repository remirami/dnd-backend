from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIRequestFactory, force_authenticate

from bestiary.models import Condition, Enemy, EnemyStats
from characters.models import Character, CharacterClass, CharacterRace, CharacterStats
from combat.models import CombatParticipant, CombatSession
from combat.views.session_views import CombatSessionViewSet
from combat.spell_rules import (
    is_buff_spell,
    apply_buff_to_target,
    remove_caster_concentration_buffs,
    BUFF_SPELL_RULES,
)
from combat.condition_effects import (
    evaluate_attack_roll_conditions,
    is_condition_immune,
    calculate_effective_speed,
)
from combat.serializers import CombatParticipantSerializer


class BuffMechanicsCombatTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user(username='buff_tester', password='password123')
        self.session = CombatSession.objects.create(status='active', current_round=1, current_turn_index=0)

        # Cleric caster
        self.cleric_class = CharacterClass.objects.create(name='cleric', hit_dice='d8', primary_ability='WIS')
        self.race = CharacterRace.objects.create(name='human', size='M', speed=30)
        self.cleric_char = Character.objects.create(
            name='Father Joseph', user=self.user, level=3, character_class=self.cleric_class, race=self.race
        )
        CharacterStats.objects.create(
            character=self.cleric_char, hit_points=25, max_hit_points=25, armor_class=16, wisdom=16, constitution=14, dexterity=10,
            spell_slots={'1': 4, '2': 2}, expended_spell_slots={'1': 0, '2': 0}
        )
        from characters.models import CharacterSpell
        CharacterSpell.objects.create(
            character=self.cleric_char, name='Shield of Faith', level=1, is_prepared=True
        )
        self.cleric_p = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='character',
            character=self.cleric_char,
            current_hp=25,
            max_hp=25,
            armor_class=16,
            initiative=15
        )

        # Fighter ally
        self.fighter_class = CharacterClass.objects.create(name='fighter', hit_dice='d10', primary_ability='STR')
        self.fighter_char = Character.objects.create(
            name='Arthur', user=self.user, level=3, character_class=self.fighter_class, race=self.race
        )
        CharacterStats.objects.create(
            character=self.fighter_char, hit_points=30, max_hit_points=30, armor_class=16, strength=16, dexterity=12
        )
        self.fighter_p = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='character',
            character=self.fighter_char,
            current_hp=30,
            max_hp=30,
            armor_class=16,
            initiative=12
        )

        # Undead enemy: Skeleton
        self.skeleton = Enemy.objects.create(name='Skeleton', hp=13, ac=13, challenge_rating='1/4', creature_type='undead')
        EnemyStats.objects.create(
            enemy=self.skeleton, strength=10, dexterity=14, constitution=15, intelligence=6, wisdom=8, charisma=5,
            hit_points=13, armor_class=13
        )
        self.skeleton_p = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='enemy',
            name='Skeleton',
            current_hp=13,
            max_hp=13,
            armor_class=13,
            initiative=8
        )

    def test_buff_spell_definitions(self):
        """Verify buff spells are correctly recognized and categorized."""
        self.assertTrue(is_buff_spell('Protection from Evil and Good'))
        self.assertTrue(is_buff_spell('Protect from Undead'))
        self.assertTrue(is_buff_spell('Shield of Faith'))
        self.assertTrue(is_buff_spell('Bless'))
        self.assertTrue(is_buff_spell('Mage Armor'))
        self.assertTrue(is_buff_spell('Haste'))
        self.assertFalse(is_buff_spell('Fireball'))

    def test_shield_of_faith_ac_bonus_and_serialization(self):
        """Shield of Faith should increase effective AC by 2 and serialize in conditions and active_buffs."""
        base_ac = self.fighter_p.calculate_effective_ac()
        self.assertEqual(base_ac, 16)

        # Apply Shield of Faith
        applied = apply_buff_to_target(self.cleric_p, self.fighter_p, 'Shield of Faith')
        self.assertIsNotNone(applied)
        self.assertTrue(self.fighter_p.has_buff('Shield of Faith'))

        # Check effective AC has increased by 2
        buffed_ac = self.fighter_p.calculate_effective_ac()
        self.assertEqual(buffed_ac, 18)

        # Check serialization
        data = CombatParticipantSerializer(self.fighter_p).data
        self.assertEqual(data['effective_ac'], 18)
        self.assertEqual(len(data['active_buffs']), 1)
        self.assertEqual(data['active_buffs'][0]['name'], 'Shield of Faith')
        # Condition list contains buff object for UI compatibility
        cond_names = [c['name'] for c in data['conditions'] if isinstance(c, dict)]
        self.assertIn('Shield of Faith', cond_names)

    def test_protection_from_evil_and_good_against_undead(self):
        """Attacking an ally buffed with Protection from Evil and Good should impart Disadvantage to Undead attackers."""
        # Baseline: normal attack conditions
        adv, disadv, reasons = evaluate_attack_roll_conditions(self.skeleton_p, self.fighter_p)
        self.assertFalse(disadv)

        # Apply Protection from Evil and Good
        apply_buff_to_target(self.cleric_p, self.fighter_p, 'Protection from Evil and Good')
        self.assertTrue(self.fighter_p.has_buff('Protection from Evil and Good'))
        self.assertTrue(self.fighter_p.has_buff('Protection from Undead'))

        # Undead attacker should now suffer Disadvantage!
        adv, disadv, reasons = evaluate_attack_roll_conditions(self.skeleton_p, self.fighter_p)
        self.assertTrue(disadv)
        self.assertTrue(any('Protection from Evil and Good' in r for r in reasons))

        # Target should also be immune to charmed and frightened
        self.assertTrue(is_condition_immune(self.fighter_p, 'charmed'))
        self.assertTrue(is_condition_immune(self.fighter_p, 'frightened'))

    def test_haste_speed_and_ac(self):
        """Haste should double walking speed and provide +2 AC."""
        apply_buff_to_target(self.cleric_p, self.fighter_p, 'Haste')
        self.assertTrue(self.fighter_p.has_buff('Haste'))
        self.assertEqual(self.fighter_p.calculate_effective_ac(), 18)
        self.assertEqual(calculate_effective_speed(self.fighter_p, 30), 60)

    def test_concentration_break_removes_buffs(self):
        """When caster's concentration breaks, buffs cast by them on allies must be removed."""
        self.cleric_p.is_concentrating = True
        self.cleric_p.concentration_spell = 'Shield of Faith'
        self.cleric_p.save()

        apply_buff_to_target(self.cleric_p, self.fighter_p, 'Shield of Faith')
        self.assertTrue(self.fighter_p.has_buff('Shield of Faith'))
        self.assertEqual(self.fighter_p.calculate_effective_ac(), 18)

        # Caster loses concentration
        remove_caster_concentration_buffs(self.cleric_p)

        # Fighter's buff should now be gone and AC back to 16
        self.fighter_p.refresh_from_db()
        self.assertFalse(self.fighter_p.has_buff('Shield of Faith'))
        self.assertEqual(self.fighter_p.calculate_effective_ac(), 16)

    def test_cast_spell_api_applies_buff(self):
        """Casting a buff spell via the API endpoint should attach the buff and return formatted info."""
        view = CombatSessionViewSet.as_view({'post': 'cast_spell'})
        request = self.factory.post(
            f'/combat/sessions/{self.session.id}/cast_spell/',
            {
                'caster_id': self.cleric_p.id,
                'target_id': self.fighter_p.id,
                'spell_name': 'Shield of Faith',
                'spell_level': 1,
                'requires_concentration': True,
            },
            format='json'
        )
        force_authenticate(request, user=self.user)
        response = view(request, pk=self.session.id)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data.get('buff_applied'), 'Shield of Faith')
        self.assertIn('Shield of Faith', response.data.get('message', ''))

        # Fighter now has active buff
        self.fighter_p.refresh_from_db()
        self.assertTrue(self.fighter_p.has_buff('Shield of Faith'))
        self.assertEqual(self.fighter_p.calculate_effective_ac(), 18)
