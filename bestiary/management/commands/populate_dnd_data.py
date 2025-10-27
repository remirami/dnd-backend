from django.core.management.base import BaseCommand
from bestiary.models import DamageType, Language


class Command(BaseCommand):
    help = 'Populate basic D&D 5e damage types and languages'

    def handle(self, *args, **options):
        # D&D 5e Damage Types
        damage_types = [
            'Acid', 'Bludgeoning', 'Cold', 'Fire', 'Force', 'Lightning',
            'Necrotic', 'Piercing', 'Poison', 'Psychic', 'Radiant', 'Slashing',
            'Thunder'
        ]
        
        for damage_type in damage_types:
            DamageType.objects.get_or_create(name=damage_type)
            self.stdout.write(f'Created damage type: {damage_type}')
        
        # Common D&D 5e Languages
        languages = [
            'Common', 'Dwarvish', 'Elvish', 'Giant', 'Gnomish', 'Goblin',
            'Halfling', 'Orc', 'Abyssal', 'Celestial', 'Draconic', 'Deep Speech',
            'Infernal', 'Primordial', 'Sylvan', 'Undercommon', 'Aquan', 'Auran',
            'Ignan', 'Terran', 'Druidic', 'Thieves\' Cant'
        ]
        
        for language in languages:
            Language.objects.get_or_create(name=language)
            self.stdout.write(f'Created language: {language}')
        
        self.stdout.write(
            self.style.SUCCESS('Successfully populated damage types and languages!')
        )
