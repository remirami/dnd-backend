from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIRequestFactory

from bestiary.models import Enemy, EnemyStats
from campaigns.models import Campaign
from encounters.models import Encounter, EncounterEnemy
from characters.models import Character, CharacterClass, CharacterRace, CharacterStats, CharacterFeature
from characters.serializers import CharacterFeatureSerializer
from combat.models import CombatParticipant, CombatSession
from combat.views.session_views import CombatSessionViewSet
from items.models import DamageType, Weapon


class FavoredEnemyAndExplorerTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user(username='ranger_tester', password='password123')
        self.session = CombatSession.objects.create(status='active', current_round=1, current_turn_index=0)

        self.ranger_class = CharacterClass.objects.create(name='ranger', hit_dice='d10', primary_ability='DEX')
        self.race = CharacterRace.objects.create(name='elf', size='M', speed=30)
        self.ranger = Character.objects.create(
            name='Strider', user=self.user, level=3, character_class=self.ranger_class, race=self.race
        )
        self.stats = CharacterStats.objects.create(
            character=self.ranger, hit_points=28, max_hit_points=28, armor_class=15,
            strength=12, dexterity=16, constitution=14, intelligence=10, wisdom=16, charisma=8
        )

        # Favored Enemy Feature on character
        self.fav_feature = CharacterFeature.objects.create(
            character=self.ranger,
            name='Favored Enemy',
            source='Ranger Level 1',
            feature_type='class',
            description='Choose a type of favored enemy: beasts, undead...',
            options=[],
            selection=['Beasts']
        )

        self.ranger_p = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='character',
            character=self.ranger,
            current_hp=28,
            max_hp=28,
            armor_class=15,
            initiative=18
        )

        # Enemies: Wolf (beast) and Skeleton (undead) and Goblin (humanoid)
        self.wolf = Enemy.objects.create(name='Dire Wolf', hp=37, ac=10, creature_type='beast', challenge_rating='1')
        EnemyStats.objects.create(
            enemy=self.wolf, strength=17, dexterity=15, constitution=15, intelligence=3, wisdom=12, charisma=7,
            hit_points=37, armor_class=10
        )
        self.wolf_p = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='enemy',
            name='Dire Wolf',
            current_hp=37,
            max_hp=37,
            armor_class=10,
            initiative=10
        )
        # Link enemy instance
        self.encounter = Encounter.objects.create(name='Wolf Encounter')
        ee = EncounterEnemy.objects.create(encounter=self.encounter, enemy=self.wolf, name='Dire Wolf', current_hp=37)
        self.wolf_p.encounter_enemy = ee
        self.wolf_p.save()

        self.goblin = Enemy.objects.create(name='Goblin', hp=7, ac=15, creature_type='humanoid', challenge_rating='1/4')
        EnemyStats.objects.create(
            enemy=self.goblin, strength=8, dexterity=14, constitution=10, intelligence=10, wisdom=8, charisma=8,
            hit_points=7, armor_class=15
        )
        self.goblin_p = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='enemy',
            name='Goblin',
            current_hp=7,
            max_hp=7,
            armor_class=15,
            initiative=5
        )
        ee_gob = EncounterEnemy.objects.create(encounter=self.encounter, enemy=self.goblin, name='Goblin', current_hp=7)
        self.goblin_p.encounter_enemy = ee_gob
        self.goblin_p.save()

    def test_serializer_fallback_options_and_selection(self):
        """Empty options on Favored Enemy / Natural Explorer are dynamically populated."""
        serializer = CharacterFeatureSerializer(self.fav_feature)
        data = serializer.data
        self.assertIn('options', data)
        self.assertIn('Beasts', data['options'])
        self.assertIn('Undead', data['options'])
        self.assertEqual(data['choice_limit'], 1)
        self.assertEqual(data['selection'], ['Beasts'])

    def test_creature_type_and_favored_enemy_detection(self):
        """Participant resolves creature type and correctly identifies favored enemies."""
        self.assertEqual(self.wolf_p.get_creature_type(), 'beast')
        self.assertEqual(self.goblin_p.get_creature_type(), 'humanoid')

        favored_list = self.ranger_p.get_favored_enemies()
        self.assertIn('beast', [f.lower() for f in favored_list])

        self.assertTrue(self.ranger_p.is_favored_enemy(self.wolf_p))
        self.assertFalse(self.ranger_p.is_favored_enemy(self.goblin_p))

    def test_favored_enemy_attack_annotation(self):
        """Attacking a favored enemy notes the favored enemy in the breakdown and response."""
        view = CombatSessionViewSet.as_view({'post': 'attack'})
        req = self.factory.post(
            f'/api/combat/sessions/{self.session.id}/attack/',
            {
                'attacker_id': self.ranger_p.id,
                'target_id': self.wolf_p.id,
                'is_ranged': False
            },
            format='json'
        )
        resp = view(req, pk=self.session.id)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data.get('is_favored_enemy'))
        self.assertEqual(resp.data.get('favored_enemy_type'), 'beast')

        if resp.data.get('hit'):
            self.assertIn('Favored Enemy', resp.data['breakdown']['damage'])

    def test_level_20_foe_slayer_damage_bonus(self):
        """Level 20 Ranger adds Wisdom modifier (+3) to damage against favored enemy."""
        self.ranger.level = 20
        self.ranger.save()

        # Set target AC to 1 so the attack hits without needing Foe Slayer on the attack roll
        self.wolf_p.armor_class = 1
        self.wolf_p.save()

        # WIS is 16 -> modifier is +3
        view = CombatSessionViewSet.as_view({'post': 'attack'})
        req = self.factory.post(
            f'/api/combat/sessions/{self.session.id}/attack/',
            {
                'attacker_id': self.ranger_p.id,
                'target_id': self.wolf_p.id,
                'dm_override': True,
                'advantage': True
            },
            format='json'
        )
        resp = view(req, pk=self.session.id)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data.get('hit'))
        self.assertIn('Foe Slayer (+3 WIS', resp.data['breakdown']['damage'])

    def test_hunters_mark_target_marked_as_favored_enemy(self):
        """Creature under Hunter's Mark is treated as favored enemy quarry."""
        # Add Hunter's Mark to ranger and target goblin
        self.ranger_p.add_buff("Hunter's Mark", source_spell="Hunter's Mark")
        if not isinstance(self.ranger_p.feature_uses, dict):
            self.ranger_p.feature_uses = {}
        self.ranger_p.feature_uses['hunters_mark_target_id'] = self.goblin_p.id
        self.ranger_p.save()

        self.assertTrue(self.ranger_p.is_favored_enemy(self.goblin_p))
