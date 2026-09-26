import random

from django.db import transaction

from bestiary.models import Enemy
from combat.models import CombatParticipant, CombatSession


def cr_to_float(cr_str):
    """Converts a CR string (e.g. '1/4', '1/2', '3') to float."""
    if not cr_str:
        return 0.0
    s = str(cr_str).strip()
    if '/' in s:
        try:
            num, den = s.split('/')
            return float(num) / float(den)
        except (ValueError, ZeroDivisionError):
            return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0


# Thematic creature type preferences per arena theme
THEME_PREFERENCES = {
    'colosseum': ['humanoid', 'beast', 'monstrosity', 'giant'],
    'crypt': ['undead', 'fiend'],
    'inferno': ['fiend', 'elemental', 'dragon'],
    'wilds': ['beast', 'plant', 'monstrosity', 'fey', 'dragon'],
    'dungeon': ['aberration', 'monstrosity', 'ooze', 'construct', 'dragon'],
}


class WaveGenerator:
    """
    Pillar 1: Procedural Wave Generator.
    Scales monster selection and encounter composition across Waves 1 to 10
    and beyond into Endless Overtime.
    """

    def get_target_cr_range(self, party_level: int, party_size: int, wave_number: int):
        """
        Determines the target CR range for minions and boss based on wave number and party level.
        Returns: (min_cr, max_cr, is_boss, count_hint)
        """
        base_cr = max(0.25, party_level * 0.5)

        if wave_number in [1, 2]:
            # Warm-up: CR 1/8 to 1/2 for lvl 1-2, slightly higher for higher levels
            min_cr = max(0.125, base_cr * 0.25)
            max_cr = max(0.25, base_cr * 0.6)
            return min_cr, max_cr, False, min(4, max(2, party_size))

        elif wave_number in [3, 4]:
            # Escalation: CR 1/4 to 1 for low lvl, up to base_cr
            min_cr = max(0.25, base_cr * 0.5)
            max_cr = max(0.5, base_cr * 1.0)
            return min_cr, max_cr, False, min(5, max(2, party_size + 1))

        elif wave_number == 5:
            # Mini-Boss Climax
            min_cr = max(1.0, base_cr * 1.2)
            max_cr = max(2.0, base_cr * 2.0)
            return min_cr, max_cr, True, 1

        elif wave_number in [6, 7]:
            # High Threat Squads
            min_cr = max(0.5, base_cr * 0.8)
            max_cr = max(1.5, base_cr * 1.5)
            return min_cr, max_cr, False, min(4, max(2, party_size))

        elif wave_number in [8, 9]:
            # Apex Predators & Casters
            min_cr = max(1.0, base_cr * 1.0)
            max_cr = max(2.5, base_cr * 2.2)
            return min_cr, max_cr, False, min(4, max(2, party_size))

        elif wave_number == 10:
            # Apex Boss Climax
            min_cr = max(2.0, base_cr * 2.0)
            max_cr = max(4.0, base_cr * 3.5)
            return min_cr, max_cr, True, 1

        else:
            # Endless Overtime (Wave > 10)
            overtime_scalar = 1.0 + (0.15 * (wave_number - 10))
            min_cr = max(2.0, base_cr * 1.5 * overtime_scalar)
            max_cr = max(4.0, base_cr * 3.0 * overtime_scalar)
            is_boss = (wave_number % 5 == 0)
            return min_cr, max_cr, is_boss, 2 if is_boss else 3

    def pick_enemies_for_wave(self, theme: str, party_level: int, party_size: int, wave_number: int):
        """
        Queries Bestiary for enemies matching the target CR range and theme.
        Returns a list of Enemy instances.
        """
        min_cr, max_cr, is_boss, count_hint = self.get_target_cr_range(party_level, party_size, wave_number)
        preferred_types = THEME_PREFERENCES.get(theme, ['humanoid', 'monstrosity', 'beast'])

        all_enemies = list(Enemy.objects.filter(hp__isnull=False, hp__gt=0))
        if not all_enemies:
            return []

        # Filter by CR range
        candidates = []
        for e in all_enemies:
            cr_val = cr_to_float(e.challenge_rating)
            if min_cr <= cr_val <= max_cr:
                candidates.append((cr_val, e))

        if not candidates:
            # Fallback: expand range
            for e in all_enemies:
                cr_val = cr_to_float(e.challenge_rating)
                if cr_val <= max_cr * 1.5:
                    candidates.append((cr_val, e))

        if not candidates:
            candidates = [(cr_to_float(e.challenge_rating), e) for e in all_enemies[:10]]

        # Prefer thematic enemies
        thematic_candidates = [item for item in candidates if item[1].creature_type in preferred_types]
        pool = thematic_candidates if thematic_candidates else candidates

        chosen = []
        if is_boss:
            # Pick highest CR in pool as boss
            pool.sort(key=lambda x: x[0], reverse=True)
            boss = pool[0][1]
            chosen.append(boss)

            # Optionally add 1-2 minion escorts if party size >= 3
            if party_size >= 3:
                minion_pool = [item[1] for item in candidates if item[0] < cr_to_float(boss.challenge_rating)]
                if minion_pool:
                    minion = random.choice(minion_pool)
                    chosen.append(minion)
                    if party_size >= 4:
                        chosen.append(minion)
        else:
            # Pick a squad
            for _ in range(count_hint):
                chosen.append(random.choice(pool)[1])

        return chosen

    @transaction.atomic
    def spawn_wave_session(self, run, wave_number: int) -> CombatSession:
        """
        Creates an active CombatSession for the given wave,
        attaching snapshot heroes and generated enemies as CombatParticipants.
        """
        enemies = self.pick_enemies_for_wave(run.theme, run.party_level, run.party_size, wave_number)

        # Create CombatSession
        session = CombatSession.objects.create(
            created_by=run.user,
            is_practice=True,
            status='active',
            current_round=1,
            current_turn_index=0,
            notes=f"Gauntlet: {run.name} - Wave {wave_number}"
        )

        # Check for active tactical boons on run
        has_ac_boon = any(b.get('type') == 'ac_boost' for b in run.active_boons)

        # 1. Add Alive Snapshot Heroes
        for hero in run.snapshot_heroes.filter(is_alive=True):
            # Calculate initiative bonus from DEX
            dex_mod = 0
            if hasattr(hero.character, 'stats') and hero.character.stats:
                dex_mod = hero.character.stats.dexterity_modifier

            init_roll = random.randint(1, 20) + dex_mod
            ac_val = 10
            if hasattr(hero.character, 'stats') and hero.character.stats and hero.character.stats.armor_class:
                ac_val = hero.character.stats.armor_class
            elif hasattr(hero.character, 'armor_class') and getattr(hero.character, 'armor_class', None):
                ac_val = hero.character.armor_class
            if has_ac_boon:
                ac_val += 2

            participant = CombatParticipant.objects.create(
                combat_session=session,
                character=hero.character,
                participant_type='character',
                current_hp=hero.current_hp,
                max_hp=hero.max_hp,
                armor_class=ac_val,
                initiative=init_roll,
                is_active=True
            )

        # 2. Add Enemies
        for idx, enemy in enumerate(enemies):
            dex_mod = 0
            if hasattr(enemy, 'stats') and enemy.stats:
                dex_mod = enemy.stats.dexterity_modifier

            init_roll = random.randint(1, 20) + dex_mod
            enemy_hp = enemy.hp or 15
            enemy_ac = enemy.ac or 12

            # Apply overtime scalar if endless
            if wave_number > 10:
                overtime_scalar = 1.0 + (0.10 * (wave_number - 10))
                enemy_hp = int(enemy_hp * overtime_scalar)

            CombatParticipant.objects.create(
                combat_session=session,
                participant_type='enemy',
                name=enemy.name,
                current_hp=enemy_hp,
                max_hp=enemy_hp,
                armor_class=enemy_ac,
                initiative=init_roll,
                is_active=True
            )

        return session
