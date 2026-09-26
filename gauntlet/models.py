import random

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

from characters.models import Character
from combat.models import CombatSession


class GauntletRun(models.Model):
    """
    Pillar 1: Gauntlet Run model.
    Encapsulates an arcade wave-survival trial with snapshot characters,
    respite rewards, and high-score tracking.
    """
    STATUS_CHOICES = [
        ('preparing', 'Preparing'),
        ('active', 'Active'),
        ('respite', 'Respite'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    THEME_CHOICES = [
        ('colosseum', 'Colosseum of Blades'),
        ('crypt', 'Crypt of the Undead'),
        ('inferno', 'Infernal Pit'),
        ('wilds', 'Savage Wilds'),
        ('dungeon', 'Sunken Dungeon'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='gauntlet_runs',
        null=True,
        blank=True,
        help_text="User who owns this Gauntlet run"
    )
    name = models.CharField(max_length=200, default="The Gauntlet")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='preparing')
    theme = models.CharField(max_length=50, choices=THEME_CHOICES, default='colosseum')
    party_level = models.IntegerField(default=1, validators=[MinValueValidator(1)])
    party_size = models.IntegerField(default=1, validators=[MinValueValidator(1)])
    current_wave = models.IntegerField(default=1, validators=[MinValueValidator(1)])
    max_waves = models.IntegerField(default=10, validators=[MinValueValidator(1)])
    is_endless = models.BooleanField(default=False, help_text="True if continuing past Wave 10 into endless overtime")
    
    current_combat_session = models.ForeignKey(
        CombatSession,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='gauntlet_runs',
        help_text="Combat session representing the active wave"
    )

    score = models.IntegerField(default=0)
    enemies_killed = models.IntegerField(default=0)
    damage_dealt = models.IntegerField(default=0)
    turns_elapsed = models.IntegerField(default=0)
    active_boons = models.JSONField(default=list, blank=True, help_text="Active tactical buffs for the next wave")

    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['score']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return f"{self.name} - Wave {self.current_wave} ({self.get_status_display()})"

    def add_hero(self, character: Character):
        """
        Creates a snapshot of the player character for this Gauntlet run.
        The persistent Character sheet is NEVER modified during the run.
        """
        if self.status != 'preparing':
            raise ValueError("Cannot add heroes to a run that has already started.")

        if self.snapshot_heroes.filter(character=character).exists():
            raise ValueError(f"Character {character.name} is already in this Gauntlet run.")

        if self.snapshot_heroes.count() >= 6:
            raise ValueError("Gauntlet party size cannot exceed 6 heroes.")

        # Resolve stats & HP
        max_hp = 10
        current_hp = 10
        spell_slots = {}

        if hasattr(character, 'stats') and character.stats:
            max_hp = character.stats.max_hit_points or character.stats.hit_points or 10
            current_hp = character.stats.hit_points or max_hp
            spell_slots = character.stats.spell_slots or {}
        elif hasattr(character, 'max_hp') and getattr(character, 'max_hp', None):
            max_hp = character.max_hp
            current_hp = getattr(character, 'current_hp', max_hp)

        if current_hp <= 0:
            current_hp = max_hp  # Enter gauntlet refreshed

        class_name = character.character_class.name if character.character_class else "Adventurer"
        hit_die = character.character_class.hit_dice if character.character_class else "d8"

        snapshot = GauntletSnapshotHero.objects.create(
            run=self,
            character=character,
            name=character.name,
            character_class=class_name,
            level=character.level or 1,
            current_hp=current_hp,
            max_hp=max_hp,
            temp_hp=0,
            hit_dice_remaining=character.level or 1,
            hit_dice_total=character.level or 1,
            hit_die_type=hit_die,
            spell_slots=spell_slots,
            is_alive=True,
            death_saves={'successes': 0, 'failures': 0}
        )

        return snapshot

    def start_run(self):
        """Initializes and launches Wave 1."""
        if self.status != 'preparing':
            raise ValueError("Gauntlet run is already active or finished.")

        hero_count = self.snapshot_heroes.count()
        if hero_count == 0:
            raise ValueError("Cannot start Gauntlet without at least 1 hero.")

        self.party_size = hero_count
        self.party_level = max(1, round(sum(h.level for h in self.snapshot_heroes.all()) / hero_count))
        self.current_wave = 1
        self.status = 'active'
        self.save()

        # Generate Wave 1
        from gauntlet.services.wave_generator import WaveGenerator
        generator = WaveGenerator()
        combat_session = generator.spawn_wave_session(self, wave_number=1)
        self.current_combat_session = combat_session
        self.save()

        return combat_session

    def sync_from_combat_session(self):
        """
        Synchronizes hero vitals and calculates wave score from the combat session.
        Called upon wave completion.
        """
        session = self.current_combat_session
        if not session or self.status in ['failed', 'completed', 'victory', 'respite']:
            return

        # Update turns elapsed
        self.turns_elapsed += session.current_round

        # Sync heroes
        for hero in self.snapshot_heroes.all():
            participant = session.participants.filter(character=hero.character).first()
            if participant:
                hero.current_hp = max(0, participant.current_hp)
                hero.is_alive = participant.is_active and participant.current_hp > 0
                hero.save()

        # Count enemies defeated in this session
        enemies_in_session = session.participants.filter(participant_type='enemy')
        dead_enemies = enemies_in_session.filter(current_hp=0).count()
        self.enemies_killed += dead_enemies

        # Wave completion bonus score: (wave * 500) + (enemies * 150)
        wave_score = (self.current_wave * 500) + (dead_enemies * 150)
        self.score += wave_score
        self.save()

    def apply_respite(self, choice_type: str, details: dict = None):
        """
        Applies chosen respite bonus between waves:
        - 'breather': Spend Hit Dice to restore HP.
        - 'arcane_surge': Regain expended spell slots.
        - 'supply_drop': Gain a healing potion / consumable.
        - 'tactical_boon': +2 AC or +10 ft speed or advantage on first strike.
        """
        details = details or {}
        results = {}

        if choice_type == 'breather':
            healed_total = 0
            for hero in self.snapshot_heroes.filter(is_alive=True):
                if hero.hit_dice_remaining > 0 and hero.current_hp < hero.max_hp:
                    # Roll hit die or take average
                    die_size = 8
                    try:
                        die_part = hero.hit_die_type.lower().replace('1d', '').replace('d', '')
                        die_size = int(die_part)
                    except (ValueError, AttributeError):
                        die_size = 8

                    # Roll hit die + level/2 bonus
                    heal_amt = random.randint(1, die_size) + max(1, hero.level // 2)
                    old_hp = hero.current_hp
                    hero.current_hp = min(hero.max_hp, hero.current_hp + heal_amt)
                    hero.hit_dice_remaining = max(0, hero.hit_dice_remaining - 1)
                    hero.save()
                    healed_total += (hero.current_hp - old_hp)

            results['message'] = f"Party took a breather, restoring {healed_total} HP."
            results['healed_hp'] = healed_total

        elif choice_type == 'arcane_surge':
            restored_count = 0
            for hero in self.snapshot_heroes.filter(is_alive=True):
                slots = hero.spell_slots or {}
                # Look for used slots
                for lvl, slot_data in slots.items():
                    if isinstance(slot_data, dict) and slot_data.get('used', 0) > 0:
                        slot_data['used'] = max(0, slot_data['used'] - 1)
                        restored_count += 1
                        break
                hero.spell_slots = slots
                hero.save()

            results['message'] = f"Arcane surge restored spell slots across {restored_count} caster(s)."
            results['restored_slots'] = restored_count

        elif choice_type == 'supply_drop':
            # Heal the lowest HP hero by 2d4+2 (Potion of Healing)
            lowest_hero = self.snapshot_heroes.filter(is_alive=True).order_by('current_hp').first()
            if lowest_hero:
                potion_heal = random.randint(1, 4) + random.randint(1, 4) + 2
                old_hp = lowest_hero.current_hp
                lowest_hero.current_hp = min(lowest_hero.max_hp, lowest_hero.current_hp + potion_heal)
                lowest_hero.save()
                results['message'] = f"Supply drop: {lowest_hero.name} drank a Potion of Healing (+{lowest_hero.current_hp - old_hp} HP)."
            else:
                results['message'] = "Supply drop received."

        elif choice_type == 'tactical_boon':
            boon_kind = details.get('boon_kind', 'ac_boost')
            if boon_kind == 'ac_boost':
                boon = {'type': 'ac_boost', 'value': 2, 'name': 'Shield Wall (+2 AC in next wave)'}
            elif boon_kind == 'speed_boost':
                boon = {'type': 'speed_boost', 'value': 10, 'name': 'Windstride (+10 ft speed)'}
            else:
                boon = {'type': 'advantage_first_strike', 'name': 'Ambush Instincts (Advantage on first strike)'}

            self.active_boons.append(boon)
            self.save()
            results['message'] = f"Tactical boon activated: {boon['name']}."
            results['boon'] = boon

        else:
            raise ValueError(f"Unknown respite choice: {choice_type}")

        self.status = 'ready_for_wave'
        self.save()
        return results

    def advance_to_next_wave(self):
        """Advances current wave and spawns new combat session."""
        alive_heroes = self.snapshot_heroes.filter(is_alive=True)
        if not alive_heroes.exists():
            self.status = 'failed'
            self.completed_at = timezone.now()
            self.save()
            raise ValueError("All heroes have fallen! The Gauntlet trial is over.")

        # Check for standard 10-wave completion
        if self.current_wave >= self.max_waves and not self.is_endless:
            self.status = 'completed'
            self.completed_at = timezone.now()
            self.save()
            return None

        old_session = self.current_combat_session

        self.current_wave += 1
        self.status = 'active'
        self.save()

        from gauntlet.services.wave_generator import WaveGenerator
        generator = WaveGenerator()
        combat_session = generator.spawn_wave_session(self, wave_number=self.current_wave)
        self.current_combat_session = combat_session

        # Clear one-wave boons
        self.active_boons = []
        self.save()

        # Clean up completed previous wave session to prevent combat archive clutter
        if old_session and old_session != combat_session:
            try:
                old_session.delete()
            except Exception:
                pass

        return combat_session


class GauntletSnapshotHero(models.Model):
    """
    Isolated in-run hero snapshot.
    Protects original Character records from permadeath or resource depletion.
    """
    run = models.ForeignKey(GauntletRun, on_delete=models.CASCADE, related_name='snapshot_heroes')
    character = models.ForeignKey(Character, on_delete=models.CASCADE, related_name='gauntlet_snapshots')
    name = models.CharField(max_length=100)
    character_class = models.CharField(max_length=50, blank=True)
    level = models.IntegerField(default=1)
    
    current_hp = models.IntegerField(default=10)
    max_hp = models.IntegerField(default=10)
    temp_hp = models.IntegerField(default=0)
    
    hit_dice_remaining = models.IntegerField(default=1)
    hit_dice_total = models.IntegerField(default=1)
    hit_die_type = models.CharField(max_length=10, default='d8')
    
    spell_slots = models.JSONField(default=dict, blank=True)
    is_alive = models.BooleanField(default=True)
    death_saves = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.name} (Lvl {self.level} {self.character_class}) - {self.current_hp}/{self.max_hp} HP"
