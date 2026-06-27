from django.core.management.base import BaseCommand
from items.models import Weapon, ItemProperty


# Map ItemProperty names → Weapon boolean field names
PROPERTY_TO_FIELD = {
    'Two-Handed': 'two_handed',
    'Light':      'light',
    'Heavy':      'heavy',
    'Finesse':    'finesse',
    'Thrown':     'thrown',
    'Ammunition': 'ammunition',
    'Loading':    'loading',
    'Reach':      'reach',
}


class Command(BaseCommand):
    help = (
        'Backfill Weapon boolean fields (two_handed, light, heavy, etc.) '
        'from the M2M properties relation. Fixes weapons imported by the old '
        'import_items_from_api command that only stored these in the M2M table.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would change without saving.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        updated = 0
        unchanged = 0

        for weapon in Weapon.objects.prefetch_related('properties').all():
            prop_names = {p.name for p in weapon.properties.all()}
            changes = {}

            for prop_name, field in PROPERTY_TO_FIELD.items():
                expected = prop_name in prop_names
                if getattr(weapon, field) != expected:
                    changes[field] = expected

            if changes:
                self.stdout.write(
                    f'  [{weapon.name}] updating: '
                    + ', '.join(f'{k}={v}' for k, v in changes.items())
                )
                if not dry_run:
                    for field, value in changes.items():
                        setattr(weapon, field, value)
                    weapon.save(update_fields=list(changes.keys()))
                updated += 1
            else:
                unchanged += 1

        prefix = '[DRY RUN] Would update' if dry_run else 'Updated'
        self.stdout.write(
            self.style.SUCCESS(
                f'\n{prefix} {updated} weapon(s). {unchanged} already correct.'
            )
        )
