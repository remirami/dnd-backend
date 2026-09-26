from django.test import TestCase
from django.contrib.auth.models import User
from unittest.mock import patch

from bestiary.models import Enemy, EnemyStats
from characters.models import Character, CharacterClass, CharacterRace, CharacterStats
from combat.models import CombatParticipant, CombatSession
from combat.utils import roll_d20
from combat.battlefield import calculate_tile_path
from combat.condition_effects import is_condition_immune
from items.models import DamageType


class RacialFeaturesCombatTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='race_tester', password='password123')
        self.session = CombatSession.objects.create(status='active', current_round=1, current_turn_index=0)
        self.fighter_class = CharacterClass.objects.create(name='fighter', hit_dice='d10', primary_ability='STR')

        # Damage types
        self.poison, _ = DamageType.objects.get_or_create(name='Poison')
        self.fire, _ = DamageType.objects.get_or_create(name='Fire')
        self.slashing, _ = DamageType.objects.get_or_create(name='Slashing')

        # Races
        self.halfling_race = CharacterRace.objects.create(name='halfling', size='S', speed=25)
        self.halforc_race = CharacterRace.objects.create(name='half-orc', size='M', speed=30)
        self.dwarf_race = CharacterRace.objects.create(name='dwarf', size='M', speed=25)
        self.tiefling_race = CharacterRace.objects.create(name='tiefling', size='M', speed=30)
        self.elf_race = CharacterRace.objects.create(name='elf', size='M', speed=30)
        self.human_race = CharacterRace.objects.create(name='human', size='M', speed=30)

    def test_halfling_lucky_reroll(self):
        """Halfling Lucky rerolls any natural 1 on d20 once."""
        # Mock random.randint to roll 1 first, then 15 on reroll
        with patch('random.randint', side_effect=[1, 15]):
            roll, breakdown = roll_d20(lucky=True)
            self.assertEqual(roll, 15)
            self.assertIn("Lucky", breakdown)

        # When lucky=False, 1 is kept
        with patch('random.randint', return_value=1):
            roll, breakdown = roll_d20(lucky=False)
            self.assertEqual(roll, 1)
            self.assertNotIn("Lucky", breakdown)

    def test_halfling_nimbleness_pathfinding(self):
        """Halflings can traverse through spaces occupied by hostile creatures larger than them."""
        # Halfling at (0, 0)
        halfling = Character.objects.create(
            name='Frodo', user=self.user, level=1, character_class=self.fighter_class, race=self.halfling_race
        )
        halfling_p = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='character',
            character=halfling,
            position_x=0,
            position_y=0,
            current_hp=10,
            max_hp=10,
            armor_class=14,
            initiative=15
        )

        # Medium hostile enemy at (5, 0)
        enemy = Enemy.objects.create(name='Orc Warrior', hp=15, ac=13, size='Medium')
        EnemyStats.objects.create(enemy=enemy, strength=16, dexterity=12, constitution=14, hit_points=15, armor_class=13)
        enemy_p = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='enemy',
            name='Orc Warrior',
            position_x=5,
            position_y=0,
            current_hp=15,
            max_hp=15,
            armor_class=13,
            initiative=10
        )

        # Normal human attempting to path straight to (10, 0) through enemy at (5, 0) with walls blocking side
        # Halfling can path through enemy square (0,0) -> (5,0) -> (10,0)
        cost, path = calculate_tile_path(self.session, halfling_p, 0, 0, 10, 0)
        self.assertNotEqual(cost, float('inf'))
        self.assertGreater(len(path), 1)

        # Human participant cannot move through hostile enemy space if path is blocked
        human = Character.objects.create(
            name='Arthur', user=self.user, level=1, character_class=self.fighter_class, race=self.human_race
        )
        human_p = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='character',
            character=human,
            position_x=0,
            position_y=0,
            current_hp=12,
            max_hp=12,
            armor_class=15,
            initiative=12
        )
        self.assertFalse(human_p.has_halfling_nimbleness())
        self.assertTrue(halfling_p.has_halfling_nimbleness())

    def test_halforc_relentless_endurance(self):
        """Half-Orc Relentless Endurance drops to 1 HP instead of 0 on lethal blow (once/long rest)."""
        halforc = Character.objects.create(
            name='Grommash', user=self.user, level=2, character_class=self.fighter_class, race=self.halforc_race
        )
        halforc_p = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='character',
            character=halforc,
            current_hp=10,
            max_hp=20,
            armor_class=14,
            initiative=12
        )

        # Lethal damage: 15 slashing damage (current_hp 10 -> drops to 1 HP instead of 0)
        new_hp, _ = halforc_p.take_damage(15, damage_type=self.slashing)
        self.assertEqual(new_hp, 1)
        self.assertTrue(halforc_p.is_active)
        self.assertTrue(halforc_p.feature_uses.get('relentless_endurance_used'))
        self.assertTrue(getattr(halforc_p, 'last_relentless_endurance_triggered', False))

        # Second lethal hit: Relentless Endurance already used, drops to 0 HP and unconscious
        new_hp2, _ = halforc_p.take_damage(5, damage_type=self.slashing)
        self.assertEqual(new_hp2, 0)
        self.assertFalse(halforc_p.is_active)

    def test_dwarven_resilience_poison_resistance(self):
        """Dwarves automatically resist poison damage (half damage)."""
        dwarf = Character.objects.create(
            name='Gimli', user=self.user, level=2, character_class=self.fighter_class, race=self.dwarf_race
        )
        dwarf_p = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='character',
            character=dwarf,
            current_hp=20,
            max_hp=20,
            armor_class=15,
            initiative=10
        )

        # 16 Poison damage -> resisted to 8
        new_hp, _ = dwarf_p.take_damage(16, damage_type=self.poison)
        self.assertEqual(new_hp, 12)
        self.assertIsNotNone(dwarf_p.last_resistance_info)
        self.assertEqual(dwarf_p.last_resistance_info['source'], 'Dwarven Resilience')

    def test_tiefling_hellish_resistance_fire(self):
        """Tieflings automatically resist fire damage (half damage)."""
        tiefling = Character.objects.create(
            name='Malakar', user=self.user, level=2, character_class=self.fighter_class, race=self.tiefling_race
        )
        tiefling_p = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='character',
            character=tiefling,
            current_hp=20,
            max_hp=20,
            armor_class=13,
            initiative=11
        )

        # 14 Fire damage -> resisted to 7
        new_hp, _ = tiefling_p.take_damage(14, damage_type=self.fire)
        self.assertEqual(new_hp, 13)
        self.assertIsNotNone(tiefling_p.last_resistance_info)
        self.assertEqual(tiefling_p.last_resistance_info['source'], 'Hellish Resistance')

    def test_elf_fey_ancestry_sleep_immunity(self):
        """Elves are immune to magical sleep condition."""
        elf = Character.objects.create(
            name='Legolas', user=self.user, level=2, character_class=self.fighter_class, race=self.elf_race
        )
        elf_p = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='character',
            character=elf,
            current_hp=18,
            max_hp=18,
            armor_class=15,
            initiative=18
        )

        self.assertTrue(elf_p.has_fey_ancestry())
        self.assertTrue(is_condition_immune(elf_p, 'unconscious', is_magical=True))
        self.assertTrue(is_condition_immune(elf_p, 'sleep', is_magical=True))
