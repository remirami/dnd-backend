from django.test import TestCase
from bestiary.parsers.action_parser import parse_action, parse_multiattack, parse_recharge, parse_trait


class ActionParserTests(TestCase):
    def test_parse_multiattack(self):
        desc = "The dragon can use its Frightful Presence. It then makes three attacks: one with its bite and two with its claws."
        res = parse_multiattack("Multiattack", desc)
        self.assertTrue(res['is_multiattack'])
        self.assertEqual(res['action_count'], 3)
        self.assertEqual(len(res['sequence']), 2)
        self.assertEqual(res['sequence'][0], {'action_name': 'Bite', 'count': 1})
        self.assertEqual(res['sequence'][1], {'action_name': 'Claw', 'count': 2})

    def test_parse_recharge(self):
        has_rec, min_roll = parse_recharge("Fire Breath (Recharge 5-6)", "")
        self.assertTrue(has_rec)
        self.assertEqual(min_roll, 5)

        has_rec2, min_roll2 = parse_recharge("Lightning Breath (Recharge 6)", "")
        self.assertTrue(has_rec2)
        self.assertEqual(min_roll2, 6)

    def test_parse_melee_attack_with_condition_rider(self):
        # Dire Wolf Bite
        name = "Bite"
        desc = "Melee Weapon Attack: +5 to hit, reach 5 ft., one target. Hit: 10 (2d6 + 3) piercing damage. If the target is a creature, it must succeed on a DC 13 Strength saving throw or be knocked prone."
        res = parse_action(name, desc)
        self.assertEqual(res['name'], "Bite")
        self.assertEqual(res['action_type'], "action")
        self.assertEqual(res['attack_type'], "melee_weapon")
        self.assertEqual(res['attack_bonus'], 5)
        self.assertIn("5 ft", res['reach_or_range'])
        self.assertEqual(res['saving_throw_dc'], 13)
        self.assertEqual(res['saving_throw_ability'], "STR")
        self.assertIn("prone", res['conditions_inflicted'])
        self.assertEqual(len(res['damage_rolls']), 1)
        dmg = res['damage_rolls'][0]
        self.assertEqual(dmg['dice_count'], 2)
        self.assertEqual(dmg['dice_sides'], 6)
        self.assertEqual(dmg['damage_bonus'], 3)
        self.assertEqual(dmg['damage_type_name'], "piercing")
        self.assertFalse(dmg['is_secondary'])

    def test_parse_saving_throw_breath_weapon(self):
        # Adult Red Dragon Fire Breath
        name = "Fire Breath (Recharge 5-6)"
        desc = "The dragon exhales fire in a 60-foot cone. Each creature in that area must make a DC 21 Dexterity saving throw, taking 63 (18d6) fire damage on a failed save, or half as much damage on a successful one."
        res = parse_action(name, desc)
        self.assertEqual(res['name'], "Fire Breath (Recharge 5-6)")
        self.assertEqual(res['attack_type'], "saving_throw")
        self.assertTrue(res['has_recharge'])
        self.assertEqual(res['recharge_min_roll'], 5)
        self.assertEqual(res['saving_throw_dc'], 21)
        self.assertEqual(res['saving_throw_ability'], "DEX")
        self.assertTrue(res['half_damage_on_save'])
        self.assertIn("60-foot cone", res['reach_or_range'])
        self.assertEqual(len(res['damage_rolls']), 1)
        dmg = res['damage_rolls'][0]
        self.assertEqual(dmg['dice_count'], 18)
        self.assertEqual(dmg['dice_sides'], 6)
        self.assertEqual(dmg['damage_type_name'], "fire")

    def test_parse_primary_plus_secondary_damage(self):
        # Giant Spider Bite: piercing + poison
        name = "Bite"
        desc = "Melee Weapon Attack: +5 to hit, reach 5 ft., one creature. Hit: 7 (1d8 + 3) piercing damage, plus 9 (2d8) poison damage."
        res = parse_action(name, desc)
        self.assertEqual(len(res['damage_rolls']), 2)
        primary = res['damage_rolls'][0]
        self.assertEqual(primary['damage_type_name'], "piercing")
        self.assertFalse(primary['is_secondary'])
        secondary = res['damage_rolls'][1]
        self.assertEqual(secondary['damage_type_name'], "poison")
        self.assertTrue(secondary['is_secondary'])
        self.assertEqual(secondary['dice_count'], 2)
        self.assertEqual(secondary['dice_sides'], 8)

    def test_parse_traits(self):
        t1 = parse_trait("Pack Tactics", "Advantage on attack rolls when ally within 5 ft.")
        self.assertEqual(t1['trait_type'], "pack_tactics")

        t2 = parse_trait("Magic Resistance", "Advantage on saving throws against spells.")
        self.assertEqual(t2['trait_type'], "magic_resistance")

        t3 = parse_trait("Keen Smell", "Advantage on Perception checks relying on smell.")
        self.assertEqual(t3['trait_type'], "keen_senses")
