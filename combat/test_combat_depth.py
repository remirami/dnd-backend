from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIRequestFactory

from bestiary.models import Condition, Enemy, EnemyStats
from characters.models import Character, CharacterClass, CharacterRace, CharacterStats, CharacterSpell
from combat.models import CombatParticipant, CombatSession
from combat.views.session_views import CombatSessionViewSet


class CombatDepthActionEconomyTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user(username='depth_tester', password='password123')
        self.session = CombatSession.objects.create(status='active', current_round=1, current_turn_index=0)

        self.incapacitated, _ = Condition.objects.get_or_create(name='incapacitated')

        # Classes
        self.fighter_class = CharacterClass.objects.create(name='fighter', hit_dice='d10', primary_ability='STR')
        self.cleric_class = CharacterClass.objects.create(name='cleric', hit_dice='d8', primary_ability='WIS')
        self.race = CharacterRace.objects.create(name='human', size='M', speed=30)

        # Hero 1: Fighter (Arthur)
        self.hero1 = Character.objects.create(
            name='Arthur', user=self.user, level=3, character_class=self.fighter_class, race=self.race
        )
        CharacterStats.objects.create(
            character=self.hero1, hit_points=28, max_hit_points=28, armor_class=16, strength=16, dexterity=12, constitution=14
        )
        self.hero1_p = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='character',
            character=self.hero1,
            current_hp=28,
            max_hp=28,
            armor_class=16,
            initiative=20,
            attacks_remaining=1,
            action_used=False,
            bonus_action_used=False
        )

        # Hero 2: Cleric (Brian)
        self.hero2 = Character.objects.create(
            name='Brian', user=self.user, level=3, character_class=self.cleric_class, race=self.race
        )
        CharacterStats.objects.create(
            character=self.hero2, hit_points=24, max_hit_points=24, armor_class=14, strength=12, dexterity=10, wisdom=16,
            spell_slots={"1": 4, "2": 2, "3": 2}, expended_spell_slots={}
        )
        CharacterSpell.objects.create(
            character=self.hero2, name='Healing Word', level=1, school='Evocation', is_prepared=True
        )
        CharacterSpell.objects.create(
            character=self.hero2, name='Fireball', level=3, school='Evocation', is_prepared=True
        )
        self.hero2_p = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='character',
            character=self.hero2,
            current_hp=24,
            max_hp=24,
            armor_class=14,
            initiative=15,
            attacks_remaining=1,
            action_used=False,
            bonus_action_used=False
        )

        # Enemy 1: Goblin 1
        self.goblin = Enemy.objects.create(name='Goblin Grunt', hp=15, ac=12, challenge_rating='1/4')
        EnemyStats.objects.create(
            enemy=self.goblin, strength=10, dexterity=14, constitution=10, intelligence=10, wisdom=10, charisma=8,
            hit_points=15, armor_class=12
        )
        self.enemy1_p = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='enemy',
            name='Goblin Grunt 1',
            current_hp=20,
            max_hp=20,
            armor_class=12,
            initiative=10
        )

        # Enemy 2: Goblin 2
        self.enemy2_p = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='enemy',
            name='Goblin Grunt 2',
            current_hp=20,
            max_hp=20,
            armor_class=12,
            initiative=8
        )

    def test_melee_flanking_grants_advantage(self):
        """Melee attack with an active ally engaged should grant Flanking advantage."""
        view = CombatSessionViewSet.as_view({'post': 'attack'})
        request = self.factory.post(
            f'/combat/sessions/{self.session.id}/attack/',
            {
                'attacker_id': self.hero1_p.id,
                'target_id': self.enemy1_p.id,
                'attack_name': 'Longsword',
                'dm_override': False,
            },
            format='json'
        )
        request.user = self.user
        response = view(request, pk=self.session.id)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data.get('is_advantage'))
        self.assertIn('Flanking', response.data.get('advantage_reasons', []))

    def test_flanking_does_not_apply_if_ally_incapacitated(self):
        """If the only other ally is incapacitated, Flanking should not apply."""
        self.hero2_p.conditions.add(self.incapacitated)
        view = CombatSessionViewSet.as_view({'post': 'attack'})
        request = self.factory.post(
            f'/combat/sessions/{self.session.id}/attack/',
            {
                'attacker_id': self.hero1_p.id,
                'target_id': self.enemy1_p.id,
                'attack_name': 'Longsword',
                'dm_override': False,
            },
            format='json'
        )
        request.user = self.user
        response = view(request, pk=self.session.id)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('Flanking', response.data.get('advantage_reasons', []))

    def test_bonus_action_spell_does_not_consume_main_action(self):
        """Casting a bonus action spell like Healing Word sets bonus_action_used but leaves attacks_remaining and action_used intact."""
        # Set turn to hero2
        self.session.current_turn_index = 1
        self.session.save()

        view = CombatSessionViewSet.as_view({'post': 'cast_spell'})
        request = self.factory.post(
            f'/combat/sessions/{self.session.id}/cast_spell/',
            {
                'caster_id': self.hero2_p.id,
                'target_id': self.hero1_p.id,
                'spell_name': 'Healing Word',
                'spell_level': 1,
                'is_healing': True,
                'damage_string': '1d4+3',
                'is_bonus_action': True,
            },
            format='json'
        )
        request.user = self.user
        response = view(request, pk=self.session.id)
        self.assertEqual(response.status_code, 200)

        # Refresh caster participant
        self.hero2_p.refresh_from_db()
        self.assertTrue(self.hero2_p.bonus_action_used)
        self.assertFalse(self.hero2_p.action_used)
        self.assertEqual(self.hero2_p.attacks_remaining, 1)

        # Attempting second bonus action in same turn should fail
        request2 = self.factory.post(
            f'/combat/sessions/{self.session.id}/cast_spell/',
            {
                'caster_id': self.hero2_p.id,
                'target_id': self.hero1_p.id,
                'spell_name': 'Healing Word',
                'spell_level': 1,
                'is_healing': True,
                'damage_string': '1d4+3',
                'is_bonus_action': True,
            },
            format='json'
        )
        request2.user = self.user
        response_second = view(request2, pk=self.session.id)
        self.assertEqual(response_second.status_code, 400)
        self.assertIn('already used their bonus action', response_second.data['error'])

    def test_multi_target_aoe_spell_resolves_all_targets(self):
        """AoE spells with target_ids should roll saves and deduct HP on every target."""
        self.session.current_turn_index = 1
        self.session.save()

        view = CombatSessionViewSet.as_view({'post': 'cast_spell'})
        request = self.factory.post(
            f'/combat/sessions/{self.session.id}/cast_spell/',
            {
                'caster_id': self.hero2_p.id,
                'target_ids': [self.enemy1_p.id, self.enemy2_p.id],
                'spell_name': 'Fireball',
                'spell_level': 3,
                'save_type': 'DEX',
                'save_dc': 14,
                'damage_string': '8d6',
                'half_on_save': True,
            },
            format='json'
        )
        request.user = self.user
        response = view(request, pk=self.session.id)
        self.assertEqual(response.status_code, 200)

        target_results = response.data.get('target_results', [])
        self.assertEqual(len(target_results), 2)

        # Refresh enemies and verify HP reduction
        self.enemy1_p.refresh_from_db()
        self.enemy2_p.refresh_from_db()
        self.assertLess(self.enemy1_p.current_hp, 20)
        self.assertLess(self.enemy2_p.current_hp, 20)
