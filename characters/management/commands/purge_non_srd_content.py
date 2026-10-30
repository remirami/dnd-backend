from django.core.management.base import BaseCommand

from characters.models import Character, CharacterBackground, Feat


class Command(BaseCommand):
    help = 'Purge non-SRD feats and backgrounds from the database based on SRD 5.2.'

    def handle(self, *args, **options):
        # 0. Get/Ensure SRD Target (Acolyte)
        acolyte = CharacterBackground.objects.filter(name__iexact='acolyte').first()
        if not acolyte:
            self.stdout.write(self.style.ERROR("Acolyte background not found. Run populate_character_data first."))
            return

        # 1. Allowed SRD 5.2 Backgrounds (case-insensitive)
        srd_background_names = ['acolyte', 'criminal', 'sage', 'soldier']
        non_srd_bgs = CharacterBackground.objects.exclude(name__iregex=r'^(' + '|'.join(srd_background_names) + r')$')
        
        # Reassign Characters with non-SRD backgrounds
        non_srd_chars = Character.objects.filter(background__in=non_srd_bgs)
        count = non_srd_chars.count()
        if count > 0:
            self.stdout.write(f"Reassigning {count} characters to '{acolyte.name}' background...")
            non_srd_chars.update(background=acolyte)
        
        # 2. Purge Non-SRD Backgrounds
        deleted_bgs, _ = non_srd_bgs.delete()
        self.stdout.write(self.style.SUCCESS(f'Deleted {deleted_bgs} non-SRD backgrounds.'))

        # 3. Allowed SRD 5.2 Feats
        srd_feat_names = [
            'Alert', 'Magic Initiate', 'Savage Attacker', 'Skilled',
            'Ability Score Improvement', 'Archery', 'Defense',
            'Great Weapon Fighting', 'Two Weapon Fighting',
            'Boon of Combat Prowess', 'Boon of Dimensional Travel', 'Boon of Fate',
            'Boon of Irresistible Offense', 'Boon of the Night Spirit',
            'Boon of Spell Recall', 'Boon of Truesight', 'Grappler'
        ]
        non_srd_feats = Feat.objects.exclude(name__in=srd_feat_names)
        deleted_feats, _ = non_srd_feats.delete()
        self.stdout.write(self.style.SUCCESS(f'Deleted {deleted_feats} non-SRD feats.'))
