from django.test import TestCase
from django.contrib.auth.models import User

from bestiary.models import Condition, DamageType, Enemy, EnemyAction, EnemyActionDamage, EnemyTrait
from characters.models import Character, CharacterClass, CharacterRace, CharacterStats
from combat.models import CombatParticipant, CombatSession


class MonsterActionsCombatTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='tester', password='password123')
        self.session = CombatSession.objects.create(status='active', current_round=1, current_turn_index=0)

        # Create Condition
        self.prone_condition, _ = Condition.objects.get_or_create(name='prone')
        self.fire_dmg, _ = DamageType.objects.get_or_create(name='fire')
        self.piercing_dmg, _ = DamageType.objects.get_or_create(name='piercing')

        # Create Reference Data
        self.char_class = CharacterClass.objects.create(
            name='fighter', hit_dice='d10', primary_ability='STR', saving_throw_proficiencies='STR,CON'
        )
        self.race = CharacterRace.objects.create(name='human', size='M', speed=30)

        # Create Player Character
        self.character = Character.objects.create(
            name='Hero', user=self.user, level=3, character_class=self.char_class, race=self.race
        )
        CharacterStats.objects.create(
            character=self.character,
            hit_points=30,
            max_hit_points=30,
            armor_class=14,
            strength=14,
            dexterity=14,
            constitution=14,
            intelligence=10,
            wisdom=10,
            charisma=10
        )
        self.char_participant = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='character',
            character=self.character,
            current_hp=30,
            max_hp=30,
            armor_class=14,
            initiative=10
        )

        # Create Dragon Enemy with Breath Weapon
        self.dragon = Enemy.objects.create(name='Red Dragon', hp=100, ac=18, challenge_rating='10')
        self.breath_action = EnemyAction.objects.create(
            enemy=self.dragon,
            name='Fire Breath (Recharge 5-6)',
            attack_type='saving_throw',
            saving_throw_dc=15,
            saving_throw_ability='DEX',
            half_damage_on_save=True,
            has_recharge=True,
            recharge_min_roll=5
        )
        EnemyActionDamage.objects.create(
            action=self.breath_action,
            dice_count=2,
            dice_sides=6,
            damage_bonus=4,
            damage_type=self.fire_dmg
        )

        self.dragon_participant = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='enemy',
            name='Red Dragon',
            current_hp=100,
            max_hp=100,
            armor_class=18,
            initiative=15
        )

    def test_recharge_state_initialization(self):
        """CombatParticipant should automatically initialize recharge_state with all recharge abilities ready."""
        self.assertIn('Fire Breath (Recharge 5-6)', self.dragon_participant.recharge_state)
        self.assertTrue(self.dragon_participant.recharge_state['Fire Breath (Recharge 5-6)'])

    def test_saving_throw_breath_weapon_via_attack_endpoint(self):
        """Calling attack with a saving_throw action should roll target saving throw and deal damage."""
        from rest_framework.test import APIRequestFactory
        from combat.views.combat_action_views import CombatActionMixin
        from combat.views.session_views import CombatSessionViewSet

        factory = APIRequestFactory()
        request = factory.post(
            f'/api/combat/sessions/{self.session.id}/attack/',
            {
                'attacker_id': self.dragon_participant.id,
                'target_id': self.char_participant.id,
                'attack_name': 'Fire Breath (Recharge 5-6)'
            },
            format='json'
        )
        view = CombatSessionViewSet.as_view({'post': 'attack'})
        response = view(request, pk=self.session.id)

        self.assertEqual(response.status_code, 200)
        self.assertIn('saving_throw', response.data)
        self.assertIn('damage', response.data)
        self.dragon_participant.refresh_from_db()
        # Should now be discharged
        self.assertFalse(self.dragon_participant.recharge_state['Fire Breath (Recharge 5-6)'])

        # Reset turn attacks remaining to test recharge lockout
        self.dragon_participant.attacks_remaining = 1
        self.dragon_participant.action_used = False
        self.dragon_participant.save()

        # Attempting to fire again while discharged should return 400
        request2 = factory.post(
            f'/api/combat/sessions/{self.session.id}/attack/',
            {
                'attacker_id': self.dragon_participant.id,
                'target_id': self.char_participant.id,
                'attack_name': 'Fire Breath (Recharge 5-6)'
            },
            format='json'
        )
        response2 = view(request2, pk=self.session.id)
        self.assertEqual(response2.status_code, 400)
        self.assertIn('recharging', response2.data['error'])

    def test_recharge_check_on_turn_reset(self):
        """check_recharges should roll d6 and recharge if roll >= min_roll."""
        self.dragon_participant.recharge_state['Fire Breath (Recharge 5-6)'] = False
        self.dragon_participant.save()

        # Mock random.randint to return 6 (success)
        import unittest.mock as mock
        with mock.patch('random.randint', return_value=6):
            recharged = self.dragon_participant.check_recharges()
            self.assertIn('Fire Breath (Recharge 5-6)', recharged)
            self.assertTrue(self.dragon_participant.recharge_state['Fire Breath (Recharge 5-6)'])

    def test_pack_tactics_advantage(self):
        """Enemy with Pack Tactics trait should have has_trait('pack_tactics') == True."""
        wolf = Enemy.objects.create(name='Dire Wolf', hp=37, ac=14, challenge_rating='1')
        EnemyTrait.objects.create(enemy=wolf, name='Pack Tactics', trait_type='pack_tactics')
        wolf_p = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='enemy',
            name='Dire Wolf',
            current_hp=37,
            max_hp=37,
            armor_class=14,
            initiative=12
        )
        self.assertTrue(wolf_p.has_trait('pack_tactics'))
        self.assertFalse(self.dragon_participant.has_trait('pack_tactics'))
