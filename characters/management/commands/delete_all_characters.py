from django.core.management.base import BaseCommand
from characters.models import Character

class Command(BaseCommand):
    help = 'Deletes ALL characters from the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force deletion without asking for confirmation',
        )

    def handle(self, *args, **options):
        count = Character.objects.count()
        
        if count == 0:
            self.stdout.write(self.style.WARNING('No characters found in the database.'))
            return

        if not options['force']:
            self.stdout.write(self.style.WARNING(f'WARNING: This will permanently delete ALL {count} characters.'))
            confirm = input("Are you sure you want to proceed? [y/N]: ")
            if confirm.lower() != 'y':
                self.stdout.write(self.style.ERROR('Operation cancelled.'))
                return

        Character.objects.all().delete()
        self.stdout.write(self.style.SUCCESS(f'Successfully deleted {count} characters.'))
