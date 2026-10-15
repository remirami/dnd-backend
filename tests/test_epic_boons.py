from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from characters.models import (
    Character,
    CharacterClass,
    CharacterClassLevel,
    CharacterFeat,
    CharacterFeature,
    CharacterRace,
    CharacterStats,
    Feat,
)

User = get_user_model()


class EpicBoonTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='epic_boon_user', password='password123')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.race = CharacterRace.objects.create(name='human')
        self.character_class = CharacterClass.objects.create(name='fighter', hit_dice='d10')

        self.character = Character.objects.create(
            user=self.user,
            name='Arthur Pendragon',
            character_class=self.character_class,
            race=self.race,
            level=19,
            pending_asi_levels=[]
        )
        self.stats = CharacterStats.objects.create(
            character=self.character,
            strength=18,
            dexterity=14,
            constitution=16,
            intelligence=10,
            wisdom=12,
            charisma=10,
            hit_points=150,
            max_hit_points=150,
            armor_class=18
        )
        CharacterClassLevel.objects.create(
            character=self.character,
            character_class=self.character_class,
            level=19
        )

        self.boon = Feat.objects.filter(category='epic_boon').first()
        if not self.boon:
            self.boon = Feat.objects.create(
                name='Boon of Combat Prowess',
                description='When you miss with a melee weapon attack, you can choose to hit instead.',
                minimum_level=20,
                category='epic_boon',
                source='SRD 5.2'
            )

    def test_epic_boon_prerequisites_level_restriction(self):
        """Epic Boons cannot be taken by characters below level 20."""
        # Character is level 19
        is_eligible, reason = self.boon.check_prerequisites(self.character)
        self.assertFalse(is_eligible)
        self.assertIn("Requires level 20", reason)

        # Level up to 20
        self.character.level = 20
        self.character.save()
        is_eligible, reason = self.boon.check_prerequisites(self.character)
        self.assertTrue(is_eligible)
        self.assertIsNone(reason)

    def test_epic_boon_single_acquisition_constraint(self):
        """Unless stated otherwise, an Epic Boon cannot be acquired more than once."""
        self.character.level = 20
        self.character.save()

        # First acquisition
        CharacterFeat.objects.create(
            character=self.character,
            feat=self.boon,
            level_taken=20
        )

        # Check prerequisite now returns False because already acquired
        is_eligible, reason = self.boon.check_prerequisites(self.character)
        self.assertFalse(is_eligible)
        self.assertIn("Already acquired", reason)

    def test_level_up_to_20_triggers_epic_boon_selection(self):
        """Leveling up from 19 to 20 automatically queues pending_asi_levels with 20."""
        response = self.client.post(f'/api/characters/{self.character.id}/level_up/')
        self.assertEqual(response.status_code, 200)

        self.character.refresh_from_db()
        self.assertEqual(self.character.level, 20)
        self.assertIn(20, self.character.pending_asi_levels)

    def test_apply_epic_boon_at_level_20(self):
        """Choosing an Epic Boon at level 20 applies the feat, creates CharacterFeature with Epic Boon source, and clears pending level."""
        self.character.level = 20
        self.character.pending_asi_levels = [20]
        self.character.save()

        response = self.client.post(
            f'/api/characters/{self.character.id}/apply_asi/',
            {
                'level': 20,
                'choice_type': 'feat',
                'feat_id': self.boon.id
            },
            format='json'
        )
        self.assertEqual(response.status_code, 200)

        self.character.refresh_from_db()
        self.assertNotIn(20, self.character.pending_asi_levels)
        self.assertTrue(CharacterFeat.objects.filter(character=self.character, feat=self.boon).exists())

        feature = CharacterFeature.objects.filter(character=self.character, name=self.boon.name).first()
        self.assertIsNotNone(feature)
        self.assertEqual(feature.source, "Epic Boon (Level 20)")
