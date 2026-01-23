"""
Populate D&D 5e feats database
"""

from django.core.management.base import BaseCommand
from characters.models import Feat


class Command(BaseCommand):
    help = 'Populate D&D 5e feats database'

    def handle(self, *args, **options):
        feats = [
            {
                'name': 'Grappler',
                'description': 'Prerequisite: Strength 13 or higher. You’ve developed the skills necessary to hold your own in close-quarters grappling. You gain the following benefits: You have advantage on attack rolls against a creature you are grappling. You can use your action to try to pin a creature grappled by you. To do so, make another grapple check. If you succeed, you and the creature are both restrained until the grapple ends.',
                'strength_requirement': 13,
                'dexterity_requirement': 0,
                'constitution_requirement': 0,
                'intelligence_requirement': 0,
                'wisdom_requirement': 0,
                'charisma_requirement': 0,
                'minimum_level': 0,
                'proficiency_requirements': '',
            },
        ]
        
        for feat_data in feats:
            feat, created = Feat.objects.update_or_create(
                name=feat_data['name'],
                defaults=feat_data
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created feat: {feat.name}'))
            else:
                self.stdout.write(self.style.SUCCESS(f'Updated feat: {feat.name}'))
        
        self.stdout.write(
            self.style.SUCCESS(f'\nSuccessfully populated {len(feats)} feats!')
        )

