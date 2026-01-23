from django.core.management.base import BaseCommand
from items.models import Item, Weapon, Armor

class Command(BaseCommand):
    help = 'Updates missing weight data for standard D&D items'

    def handle(self, *args, **options):
        # Standard D&D 5e armor weights (in pounds)
        armor_weights = {
            'Padded': 8,
            'Leather': 10,
            'Studded Leather': 13,
            'Hide': 12,
            'Chain Shirt': 20,
            'Scale Mail': 45,
            'Breastplate': 20,
            'Half Plate': 40,
            'Ring Mail': 40,
            'Chain Mail': 55,
            'Splint': 60,
            'Plate': 65,
            'Shield': 6,
        }

        # Standard D&D 5e weapon weights (in pounds)
        weapon_weights = {
            'Club': 2,
            'Dagger': 1,
            'Greatclub': 10,
            'Handaxe': 2,
            'Javelin': 2,
            'Light Hammer': 2,
            'Mace': 4,
            'Quarterstaff': 4,
            'Sickle': 2,
            'Spear': 3,
            'Light Crossbow': 5,
            'Dart': 0.25,
            'Shortbow': 2,
            'Sling': 0,
            'Battleaxe': 4,
            'Flail': 2,
            'Glaive': 6,
            'Greataxe': 7,
            'Greatsword': 6,
            'Halberd': 6,
            'Lance': 6,
            'Longsword': 3,
            'Maul': 10,
            'Morningstar': 4,
            'Pike': 18,
            'Rapier': 2,
            'Scimitar': 3,
            'Shortsword': 2,
            'Trident': 4,
            'War Pick': 2,
            'Warhammer': 2,
            'Whip': 3,
            'Blowgun': 1,
            'Hand Crossbow': 3,
            'Heavy Crossbow': 18,
            'Longbow': 2,
            'Net': 3,
        }

        updated_count = 0

        # Update armor weights
        self.stdout.write('Updating armor weights...')
        for name, weight in armor_weights.items():
            try:
                armor = Armor.objects.get(name__iexact=name)
                if armor.weight == 0:
                    armor.weight = weight
                    armor.save()
                    updated_count += 1
                    self.stdout.write(f'  Updated {name}: {weight} lb')
            except Armor.DoesNotExist:
                self.stdout.write(self.style.WARNING(f'  Armor not found: {name}'))
            except Armor.MultipleObjectsReturned:
                self.stdout.write(self.style.WARNING(f'  Multiple armors found for: {name}'))

        # Update weapon weights
        self.stdout.write('\nUpdating weapon weights...')
        for name, weight in weapon_weights.items():
            try:
                weapon = Weapon.objects.get(name__iexact=name)
                if weapon.weight == 0:
                    weapon.weight = weight
                    weapon.save()
                    updated_count += 1
                    self.stdout.write(f'  Updated {name}: {weight} lb')
            except Weapon.DoesNotExist:
                self.stdout.write(self.style.WARNING(f'  Weapon not found: {name}'))
            except Weapon.MultipleObjectsReturned:
                self.stdout.write(self.style.WARNING(f'  Multiple weapons found for: {name}'))

        self.stdout.write(self.style.SUCCESS(f'\nSuccessfully updated {updated_count} items'))
