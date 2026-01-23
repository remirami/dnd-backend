from django.core.management.base import BaseCommand
from characters.models import Feat, CharacterBackground, Character

class Command(BaseCommand):
    help = 'Purge all non-SRD feats and backgrounds from the database.'

    def handle(self, *args, **options):
        # 0. Get/Ensure SRD Target (Acolyte)
        try:
            acolyte = CharacterBackground.objects.get(name='acolyte')
        except CharacterBackground.DoesNotExist:
            self.stdout.write(self.style.ERROR("Acolyte background not found. Run populate_character_data first."))
            return

        # 1. Reassign Characters with non-SRD backgrounds
        srd_backgrounds = ['acolyte']
        non_srd_chars = Character.objects.exclude(background__name__in=srd_backgrounds).exclude(background__isnull=True)
        count = non_srd_chars.count()
        if count > 0:
            self.stdout.write(f"Reassigning {count} characters to 'acolyte' background...")
            non_srd_chars.update(background=acolyte)
        
        # 2. Purge Backgrounds
        deleted_bgs, _ = CharacterBackground.objects.exclude(name__in=srd_backgrounds).delete()
        self.stdout.write(self.style.SUCCESS(f'Deleted {deleted_bgs} non-SRD backgrounds.'))

        # 3. Purge Feats (Keep only Grappler)
        srd_feats = ['Grappler']
        deleted_feats, _ = Feat.objects.exclude(name__in=srd_feats).delete()
        self.stdout.write(self.style.SUCCESS(f'Deleted {deleted_feats} non-SRD feats.'))
