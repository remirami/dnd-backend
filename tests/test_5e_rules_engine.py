"""
Comprehensive tests for Phase 5.6: 5e Mechanical Correctness & Rules Engine.
Covers:
- Phase 1a & 1b: Resistance, Immunity, Vulnerability & Damage Type Propagation
- Phase 2: Spell Range Validation (Self, Touch, Ranged)
- Phase 3: Condition Immunity Enforcement
- Phase 4: Enemy Action Range & Reach Enforcement
- Phase 5: Spell Rules (Healing undead restrictions, post-effects riders)
"""
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from bestiary.models import (
    Condition,
    DamageType,
    Enemy,
    EnemyAction,
    EnemyConditionImmunity,
    EnemyResistance,
    EnemyStats,
)
from characters.models import Character, CharacterClass, CharacterRace, CharacterSpell, CharacterStats
from combat.combat_ai import _check_action_range, _execute_attack
from combat.condition_effects import auto_apply_condition_from_spell, is_condition_immune
from combat.models import CombatParticipant, CombatSession, Encounter, EncounterEnemy
from combat.spell_rules import apply_spell_post_effects, can_heal_target


class FiveERulesEngineTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Damage types
        self.fire_dt, _ = DamageType.objects.get_or_create(name="Fire")
        self.cold_dt, _ = DamageType.objects.get_or_create(name="Cold")
        self.necrotic_dt, _ = DamageType.objects.get_or_create(name="Necrotic")
        self.radiant_dt, _ = DamageType.objects.get_or_create(name="Radiant")
        self.slashing_dt, _ = DamageType.objects.get_or_create(name="Slashing")
        self.bludgeoning_dt, _ = DamageType.objects.get_or_create(name="Bludgeoning")

        # Conditions
        self.prone_cond, _ = Condition.objects.get_or_create(name="prone")
        self.paralyzed_cond, _ = Condition.objects.get_or_create(name="paralyzed")
        self.poisoned_cond, _ = Condition.objects.get_or_create(name="poisoned")

        # Wizard character
        self.char_class = CharacterClass.objects.create(name="wizard", hit_dice="d6")
        self.race = CharacterRace.objects.create(name="elf")
        self.character = Character.objects.create(
            name="Valeros",
            level=5,
            character_class=self.char_class,
            race=self.race
        )
        self.char_stats = CharacterStats.objects.create(
            character=self.character,
            hit_points=30,
            max_hit_points=30,
            armor_class=12,
            spell_slots={"1": 4, "2": 3, "3": 2},
            expended_spell_slots={"1": 0, "2": 0, "3": 0}
        )

        # Spells known/prepared
        CharacterSpell.objects.create(
            character=self.character,
            name="Fireball",
            level=3,
            is_prepared=True
        )
        CharacterSpell.objects.create(
            character=self.character,
            name="Shield",
            level=1,
            is_prepared=True
        )
        CharacterSpell.objects.create(
            character=self.character,
            name="Cure Wounds",
            level=1,
            is_prepared=True
        )
        CharacterSpell.objects.create(
            character=self.character,
            name="Magic Missile",
            level=1,
            is_prepared=True
        )
        CharacterSpell.objects.create(
            character=self.character,
            name="Grease",
            level=1,
            is_prepared=True
        )
        CharacterSpell.objects.create(
            character=self.character,
            name="Fog Cloud",
            level=1,
            is_prepared=True
        )

        # Enemies
        # 1. Fire Elemental (Immune to Fire, Resistant to non-magical)
        self.fire_elemental = Enemy.objects.create(
            name="Fire Elemental",
            hp=102,
            ac=13,
            creature_type="elemental"
        )
        EnemyStats.objects.create(
            enemy=self.fire_elemental,
            hit_points=102,
            armor_class=13,
            strength=10,
            dexterity=17,
            constitution=16
        )
        EnemyResistance.objects.create(
            enemy=self.fire_elemental,
            damage_type=self.fire_dt,
            resistance_type="immunity"
        )
        EnemyConditionImmunity.objects.create(
            enemy=self.fire_elemental,
            condition=self.paralyzed_cond
        )
        EnemyConditionImmunity.objects.create(
            enemy=self.fire_elemental,
            condition=self.prone_cond
        )

        # 2. Skeleton (Vulnerable to Bludgeoning, Immune to Poisoned, Undead)
        self.skeleton = Enemy.objects.create(
            name="Skeleton",
            hp=13,
            ac=13,
            creature_type="undead"
        )
        EnemyStats.objects.create(
            enemy=self.skeleton,
            hit_points=13,
            armor_class=13,
            strength=10,
            dexterity=14,
            constitution=15
        )
        EnemyResistance.objects.create(
            enemy=self.skeleton,
            damage_type=self.bludgeoning_dt,
            resistance_type="vulnerability"
        )
        EnemyConditionImmunity.objects.create(
            enemy=self.skeleton,
            condition=self.poisoned_cond
        )

        # Combat session
        self.encounter = Encounter.objects.create(name="Rules Test Encounter")
        self.session = CombatSession.objects.create(
            encounter=self.encounter,
            status='active',
            current_round=1,
            current_turn_index=0
        )

        # Participants
        self.caster_p = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='character',
            character=self.character,
            current_hp=30,
            max_hp=30,
            armor_class=12,
            position_x=10,
            position_y=10,
            initiative=20
        )

        self.ee_elemental = EncounterEnemy.objects.create(
            encounter=self.encounter,
            enemy=self.fire_elemental,
            name="Fire Elemental 1",
            current_hp=102
        )
        self.elemental_p = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='enemy',
            encounter_enemy=self.ee_elemental,
            current_hp=102,
            max_hp=102,
            armor_class=13,
            position_x=10,
            position_y=15,  # 5 ft away (adjacent)
            initiative=15
        )

        self.ee_skeleton = EncounterEnemy.objects.create(
            encounter=self.encounter,
            enemy=self.skeleton,
            name="Skeleton 1",
            current_hp=13
        )
        self.skeleton_p = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='enemy',
            encounter_enemy=self.ee_skeleton,
            current_hp=13,
            max_hp=13,
            armor_class=13,
            position_x=10,
            position_y=40,  # 30 ft away
            initiative=10
        )

    # -------------------------------------------------------------
    # Phase 1a & 1b: Resistance Engine & Damage Type Propagation
    # -------------------------------------------------------------
    def test_damage_immunity_takes_zero_damage(self):
        """Fire Elemental takes 0 damage from Fire damage."""
        hp_before = self.elemental_p.current_hp
        new_hp, _ = self.elemental_p.take_damage(20, damage_type='Fire')
        self.assertEqual(new_hp, hp_before)
        self.assertEqual(self.elemental_p.last_resistance_info['type'], 'immunity')

    def test_damage_vulnerability_takes_double_damage(self):
        """Skeleton takes double damage from Bludgeoning damage."""
        new_hp, _ = self.skeleton_p.take_damage(5, damage_type='Bludgeoning')
        # 5 * 2 = 10 damage -> 13 - 10 = 3 HP
        self.assertEqual(new_hp, 3)
        self.assertEqual(self.skeleton_p.last_resistance_info['type'], 'vulnerability')

    def test_damage_resistance_takes_half_damage(self):
        """Register Cold resistance and verify half damage."""
        EnemyResistance.objects.create(
            enemy=self.skeleton,
            damage_type=self.cold_dt,
            resistance_type="resistance"
        )
        new_hp, _ = self.skeleton_p.take_damage(10, damage_type='Cold')
        # 10 // 2 = 5 damage -> 13 - 5 = 8 HP
        self.assertEqual(new_hp, 8)
        self.assertEqual(self.skeleton_p.last_resistance_info['type'], 'resistance')

    # -------------------------------------------------------------
    # Phase 2: Spell Range Validation
    # -------------------------------------------------------------
    def test_touch_spell_fails_when_target_is_out_of_reach(self):
        """Cure Wounds (Touch) fails when target is 30 ft away."""
        response = self.client.post(
            f'/api/combat/sessions/{self.session.id}/cast_spell/',
            {
                'caster_id': self.caster_p.id,
                'target_id': self.skeleton_p.id,  # 30 ft away
                'spell_name': 'Cure Wounds',
                'spell_level': 1,
                'damage_string': '1d8+3'
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Touch spell", response.data['error'])
        self.assertIn("30 ft away", response.data['error'])

    def test_self_spell_fails_when_targeting_other_creature(self):
        """Shield (range: Self) fails when targeted at an enemy."""
        response = self.client.post(
            f'/api/combat/sessions/{self.session.id}/cast_spell/',
            {
                'caster_id': self.caster_p.id,
                'target_id': self.elemental_p.id,
                'spell_name': 'Shield',
                'spell_level': 1,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("can only target yourself", response.data['error'])

    def test_ranged_spell_within_range_succeeds(self):
        """Fireball (range 150 ft) succeeds on target 30 ft away."""
        response = self.client.post(
            f'/api/combat/sessions/{self.session.id}/cast_spell/',
            {
                'caster_id': self.caster_p.id,
                'target_id': self.skeleton_p.id,  # 30 ft away <= 150 ft
                'spell_name': 'Fireball',
                'spell_level': 3,
                'damage_string': '8d6'
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # -------------------------------------------------------------
    # Phase 3: Condition Immunity Enforcement
    # -------------------------------------------------------------
    def test_condition_immunity_blocks_spell_condition(self):
        """Fire Elemental is immune to paralyzed, Hold Person condition is not applied."""
        self.assertTrue(is_condition_immune(self.elemental_p, 'paralyzed'))
        res = auto_apply_condition_from_spell(self.elemental_p, 'Hold Person')
        self.assertIsNone(res)
        self.assertEqual(self.elemental_p.last_condition_immune, 'paralyzed')
        self.assertFalse(self.elemental_p.conditions.filter(name='paralyzed').exists())

    def test_condition_applied_when_not_immune(self):
        """Skeleton is not immune to paralyzed, Hold Person applies paralyzed."""
        self.assertFalse(is_condition_immune(self.skeleton_p, 'paralyzed'))
        res = auto_apply_condition_from_spell(self.skeleton_p, 'Hold Person')
        self.assertIsNotNone(res)
        self.assertTrue(self.skeleton_p.conditions.filter(name='paralyzed').exists())

    # -------------------------------------------------------------
    # Phase 4: Enemy Action Range Enforcement
    # -------------------------------------------------------------
    def test_enemy_melee_attack_out_of_range_fails(self):
        """Melee action with 5 ft reach fails against target 30 ft away."""
        bite_action = EnemyAction.objects.create(
            enemy=self.skeleton,
            name="Shortsword",
            attack_type="melee_weapon",
            reach_or_range="5 ft.",
            attack_bonus=4
        )
        in_range, _, dist, max_r = _check_action_range(
            self.skeleton_p, self.caster_p, bite_action, default_reach=5
        )
        self.assertFalse(in_range)
        self.assertEqual(dist, 30)
        self.assertEqual(max_r, 5)

        # Executing the attack produces an out-of-range miss with 0 damage
        res = _execute_attack(
            self.session, self.skeleton_p, self.caster_p,
            {'name': 'Shortsword', 'bonus': 4, 'damage': '1d6+2', 'action_obj': bite_action}
        )
        self.assertFalse(res['hit'])
        self.assertTrue(res['out_of_range'])
        self.assertEqual(res['damage'], 0)

    def test_enemy_melee_attack_in_range_succeeds(self):
        """Melee action with 5 ft reach succeeds against adjacent target (5 ft away)."""
        slam_action = EnemyAction.objects.create(
            enemy=self.fire_elemental,
            name="Touch",
            attack_type="melee_weapon",
            reach_or_range="5 ft.",
            attack_bonus=6
        )
        in_range, _, dist, _ = _check_action_range(
            self.elemental_p, self.caster_p, slam_action, default_reach=5
        )
        self.assertTrue(in_range)
        self.assertEqual(dist, 5)

    # -------------------------------------------------------------
    # Phase 5: Spell Rules (Undead healing restriction & riders)
    # -------------------------------------------------------------
    def test_cure_wounds_cannot_heal_undead(self):
        """Cure Wounds has no effect on undead creatures."""
        self.assertFalse(can_heal_target(self.skeleton_p, 'Cure Wounds'))
        self.assertTrue(can_heal_target(self.caster_p, 'Cure Wounds'))

    def test_shocking_grasp_rider_prevents_reactions(self):
        """Shocking Grasp prevents target from taking reactions."""
        self.assertFalse(self.skeleton_p.reaction_used)
        effects = apply_spell_post_effects(self.caster_p, self.skeleton_p, 'Shocking Grasp', hit_or_save_failed=True)
        self.skeleton_p.refresh_from_db()
        self.assertTrue(self.skeleton_p.reaction_used)
        self.assertTrue(any("cannot take reactions" in e for e in effects))

    def test_ray_of_frost_rider_reduces_speed(self):
        """Ray of Frost reduces target speed by 10 ft."""
        self.assertEqual(self.skeleton_p.speed, 30)
        effects = apply_spell_post_effects(self.caster_p, self.skeleton_p, 'Ray of Frost', hit_or_save_failed=True)
        self.skeleton_p.refresh_from_db()
        self.assertEqual(self.skeleton_p.speed, 20)
        self.assertTrue(any("speed is reduced by 10 ft" in e for e in effects))

    # -------------------------------------------------------------
    # Phase 6: Magic Missile 5e Multi-Dart Mechanics
    # -------------------------------------------------------------
    def test_magic_missile_fires_3_darts_at_single_target(self):
        """Magic missile cast at 1st level fires 3 darts at a single target (1d4+1 each)."""
        initial_hp = self.skeleton_p.current_hp
        response = self.client.post(
            f'/api/combat/sessions/{self.session.id}/cast_spell/',
            {
                'caster_id': self.caster_p.id,
                'target_id': self.skeleton_p.id,
                'spell_name': 'Magic Missile',
                'spell_level': 1,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        target_results = response.data['target_results']
        self.assertEqual(len(target_results), 1)
        res = target_results[0]
        self.assertEqual(res['darts_count'], 3)
        self.assertEqual(len(res['dart_rolls']), 3)
        for roll in res['dart_rolls']:
            self.assertGreaterEqual(roll, 2)  # 1d4 + 1 min 2
            self.assertLessEqual(roll, 5)     # 1d4 + 1 max 5
        total_dmg = sum(res['dart_rolls'])
        self.assertEqual(res['damage'], total_dmg)
        self.assertEqual(response.data['damage'], total_dmg)
        self.skeleton_p.refresh_from_db()
        self.assertEqual(self.skeleton_p.current_hp, max(0, initial_hp - total_dmg))
        self.assertIn("striking Skeleton 1 with 3 darts", response.data['action']['description'])

    def test_magic_missile_upcast_fires_4_darts(self):
        """Magic missile upcast to 2nd level fires 4 darts."""
        response = self.client.post(
            f'/api/combat/sessions/{self.session.id}/cast_spell/',
            {
                'caster_id': self.caster_p.id,
                'target_id': self.skeleton_p.id,
                'spell_name': 'Magic Missile',
                'spell_level': 2,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        target_results = response.data['target_results']
        self.assertEqual(len(target_results), 1)
        res = target_results[0]
        self.assertEqual(res['darts_count'], 4)
        self.assertEqual(len(res['dart_rolls']), 4)
        self.assertEqual(res['damage'], sum(res['dart_rolls']))

    def test_magic_missile_split_across_multiple_targets(self):
        """Magic missile can divide darts across different targets."""
        response = self.client.post(
            f'/api/combat/sessions/{self.session.id}/cast_spell/',
            {
                'caster_id': self.caster_p.id,
                'target_ids': [self.skeleton_p.id, self.skeleton_p.id, self.elemental_p.id],
                'spell_name': 'Magic Missile',
                'spell_level': 1,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        target_results = response.data['target_results']
        self.assertEqual(len(target_results), 2)
        skel_res = next(r for r in target_results if r['target_id'] == self.skeleton_p.id)
        elem_res = next(r for r in target_results if r['target_id'] == self.elemental_p.id)
        self.assertEqual(skel_res['darts_count'], 2)
        self.assertEqual(elem_res['darts_count'], 1)

    def test_magic_missile_negated_by_shield_spell(self):
        """Target protected by Shield spell completely negates all Magic Missile darts."""
        # Activate shield spell on target
        self.skeleton_p.feature_uses = {'shield_spell_active': True}
        self.skeleton_p.save(update_fields=['feature_uses'])
        initial_hp = self.skeleton_p.current_hp

        response = self.client.post(
            f'/api/combat/sessions/{self.session.id}/cast_spell/',
            {
                'caster_id': self.caster_p.id,
                'target_id': self.skeleton_p.id,
                'spell_name': 'Magic Missile',
                'spell_level': 1,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        target_results = response.data['target_results']
        res = target_results[0]
        self.assertTrue(res['shield_negated'])
        self.assertEqual(res['damage'], 0)
        self.skeleton_p.refresh_from_db()
        self.assertEqual(self.skeleton_p.current_hp, initial_hp)
        self.assertIn("Shield spell absorbs all 3 darts", response.data['action']['description'])

    # -------------------------------------------------------------
    # Phase 7: Difficult Terrain & Tile-by-Tile Pathfinding
    # -------------------------------------------------------------
    def test_grease_spell_creates_difficult_terrain_effect(self):
        """Casting Grease creates an EnvironmentalEffect of difficult terrain and prone save."""
        response = self.client.post(
            f'/api/combat/sessions/{self.session.id}/cast_spell/',
            {
                'caster_id': self.caster_p.id,
                'target_id': self.skeleton_p.id,
                'spell_name': 'Grease',
                'spell_level': 1,
                'save_type': 'DEX',
                'save_dc': 13,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Verify EnvironmentalEffect exists on session
        effect = self.session.environmental_effects.filter(effect_type='terrain').first()
        self.assertIsNotNone(effect)
        self.assertIn("Grease", effect.description)
        self.assertEqual(effect.cover_area_x, self.skeleton_p.position_x)
        self.assertEqual(effect.cover_area_y, self.skeleton_p.position_y)

    def test_difficult_terrain_movement_cost_tile_by_tile(self):
        """
        Stepping into difficult terrain tile costs 10 ft instead of 5 ft.
        Cannot skip difficult terrain: path cost must be fully paid.
        """
        from combat.models import EnvironmentalEffect
        # Create a 10-ft square of difficult terrain centered at (15, 10) (col 3, row 2)
        EnvironmentalEffect.objects.create(
            combat_session=self.session,
            effect_type='terrain',
            terrain_type='mud',
            cover_area_x=15,
            cover_area_y=10,
            cover_area_radius=5,
            description="Grease Puddle"
        )

        # Place caster at (10, 10) (col 2, row 2), with 10 ft movement remaining
        self.caster_p.position_x = 10
        self.caster_p.position_y = 10
        self.caster_p.movement_used = 20  # 30 - 20 = 10 ft left
        self.caster_p.save()

        # Target (20, 10) is 10 ft away as straight Chebyshev distance,
        # but stepping onto (15, 10) [difficult terrain, cost 10] then (20, 10) [difficult terrain, cost 10]
        # costs 20 ft total!
        # With only 10 ft of movement remaining, moving to (20, 10) MUST fail!
        response = self.client.post(
            f'/api/combat/sessions/{self.session.id}/move/',
            {
                'participant_id': self.caster_p.id,
                'target_x': 20,
                'target_y': 10,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Not enough movement", response.data['error'])
        self.assertIn("20 ft", response.data['error'])

        # Now give caster 20 ft of movement (movement_used = 10)
        self.caster_p.movement_used = 10  # 30 - 10 = 20 ft left
        self.caster_p.save()

        response = self.client.post(
            f'/api/combat/sessions/{self.session.id}/move/',
            {
                'participant_id': self.caster_p.id,
                'target_x': 20,
                'target_y': 10,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.caster_p.refresh_from_db()
        self.assertEqual(self.caster_p.position_x, 20)
        self.assertEqual(self.caster_p.position_y, 10)
        # Movement used increased by exactly 20 ft (path cost through 2 difficult terrain tiles), not just 10 ft!
        self.assertEqual(self.caster_p.movement_used, 30)

    def test_cannot_move_into_solid_obstacle(self):
        """Moving into a solid obstacle tile is rejected."""
        from combat.battlefield import get_battlefield_layout
        layout = get_battlefield_layout(self.session.id)
        # Find a solid obstacle in the active session's layout
        feat = next(f for f in layout['features'] if f.get('blocks_movement'))
        target_x = feat['col'] * 5
        target_y = feat['row'] * 5

        # Place caster adjacent to the obstacle
        self.caster_p.position_x = max(0, target_x - 5)
        self.caster_p.position_y = target_y
        self.caster_p.movement_used = 0
        self.caster_p.save()

        response = self.client.post(
            f'/api/combat/sessions/{self.session.id}/move/',
            {
                'participant_id': self.caster_p.id,
                'target_x': target_x,
                'target_y': target_y,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("obstacle", response.data['error'].lower())
