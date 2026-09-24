from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from characters.models import Character
from combat.models import CombatParticipant, CombatSession
from items.models import DamageType, Weapon


class WeaponRangesAndThrownTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='rangemaster', password='password123')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        piercing, _ = DamageType.objects.get_or_create(name='Piercing')

        # Create or update Javelin
        self.javelin, _ = Weapon.objects.get_or_create(
            name='Javelin',
            defaults={
                'weapon_type': 'simple_melee',
                'damage_dice': '1d6',
                'damage_type': piercing,
                'thrown': True,
                'range_normal': 30,
                'range_long': 120,
            }
        )

        # Create or update Shortbow
        self.shortbow, _ = Weapon.objects.get_or_create(
            name='Shortbow',
            defaults={
                'weapon_type': 'simple_ranged',
                'damage_dice': '1d6',
                'damage_type': piercing,
                'ammunition': True,
                'two_handed': True,
                'range_normal': 80,
                'range_long': 320,
            }
        )

        from characters.models import CharacterClass, CharacterRace, CharacterStats
        fighter_class, _ = CharacterClass.objects.get_or_create(name='fighter')
        human_race, _ = CharacterRace.objects.get_or_create(name='human')
        self.character = Character.objects.create(
            user=self.user,
            name='Grak the Skewerer',
            character_class=fighter_class,
            race=human_race,
            level=3,
        )
        self.stats = CharacterStats.objects.create(
            character=self.character,
            strength=16,
            dexterity=12,
            constitution=14,
            speed=30,
            hit_points=28,
            max_hit_points=28,
            armor_class=15,
        )

        from encounters.models import Encounter
        self.encounter = Encounter.objects.create(name='Range Range Combat')
        self.session = CombatSession.objects.create(
            encounter=self.encounter,
            status='active',
            current_round=1,
            current_turn_index=0,
        )

        # Hero at (0, 0)
        self.hero_part = CombatParticipant.objects.create(
            combat_session=self.session,
            character=self.character,
            participant_type='character',
            initiative=20,
            current_hp=28,
            max_hp=28,
            armor_class=15,
            is_active=True,
            attacks_remaining=1,
            action_used=False,
            position_x=0,
            position_y=0,
        )

        # Enemy at (20, 0) - 20 ft away (beyond 5ft melee reach)
        self.enemy_part = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='enemy',
            name='Goblin Archer',
            initiative=10,
            current_hp=12,
            max_hp=12,
            armor_class=13,
            is_active=True,
            position_x=20,
            position_y=0,
        )

    def test_javelin_thrown_beyond_melee_reach(self):
        """Throwing a javelin at a target 20 ft away should succeed as a thrown ranged attack using STR."""
        url = f'/api/combat/sessions/{self.session.id}/attack/'
        res = self.client.post(url, {
            'action_type': 'attack',
            'attacker_id': self.hero_part.id,
            'target_id': self.enemy_part.id,
            'attack_name': 'Javelin',
        }, format='json')

        self.assertEqual(res.status_code, 200, res.data)
        self.assertIn('hit', res.data)
        # Verify STR (+3) + Prof (+2)
        breakdown = res.data.get('breakdown', {})
        self.assertIn('Ability: +3', breakdown.get('attack', ''))
        self.assertIn('Proficiency: +2', breakdown.get('attack', ''))

    def test_shortbow_ranged_attack(self):
        """Shortbow at 20 ft should succeed as a ranged attack using DEX."""
        url = f'/api/combat/sessions/{self.session.id}/attack/'
        res = self.client.post(url, {
            'action_type': 'attack',
            'attacker_id': self.hero_part.id,
            'target_id': self.enemy_part.id,
            'attack_name': 'Shortbow',
        }, format='json')

        self.assertEqual(res.status_code, 200, res.data)
        self.assertIn('hit', res.data)
        # Verify DEX (+1) + Prof (+2)
        breakdown = res.data.get('breakdown', {})
        self.assertIn('Ability: +1', breakdown.get('attack', ''))
        self.assertIn('Proficiency: +2', breakdown.get('attack', ''))

    def test_javelin_beyond_long_range_rejected(self):
        """Target 125 ft away is beyond Javelin's 120 ft long range and should be rejected."""
        self.enemy_part.position_x = 125
        self.enemy_part.save(update_fields=['position_x'])

        url = f'/api/combat/sessions/{self.session.id}/attack/'
        res = self.client.post(url, {
            'action_type': 'attack',
            'attacker_id': self.hero_part.id,
            'target_id': self.enemy_part.id,
            'attack_name': 'Javelin',
        }, format='json')

        self.assertEqual(res.status_code, 400)
        self.assertIn('beyond weapon range', res.data.get('error', ''))
