"""
Tests for Official SRD 5.2 Subclass Specializations (Phase 6)

Covers:
1. Fighter — Champion: Improved Critical (19-20), Superior Critical (18-20), Remarkable Athlete, Survivor.
2. Ranger — Hunter: Colossus Slayer (+1d8 extra damage against damaged targets once/turn).
3. Warlock — Fiend Patron: Dark One's Blessing (temporary HP upon reducing hostile to 0 HP).
4. Monk — Warrior of the Open Hand: Open Hand Technique (Topple, 15ft Push, No Reactions), Wholeness of Body.
5. Rogue — Thief: Fast Hands (Bonus action item / Use an Object, Cunning Action options).
"""

from unittest.mock import patch
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APITestCase

from bestiary.models import Condition
from characters.models import Character, CharacterClass, CharacterRace, CharacterStats
from combat.models import CombatParticipant, CombatSession
from combat.subclasses import (
    apply_champion_survivor,
    apply_elemental_affinity_damage,
    activate_elemental_affinity_resistance,
    can_use_cutting_words,
    get_bardic_inspiration_die,
    get_critical_threshold,
    get_draconic_ancestor_element,
    get_natural_recovery_limit,
    has_elemental_affinity_resistance,
    has_lands_stride,
    has_natures_ward,
    is_champion,
    is_draconic_sorcerer,
    is_fiend_warlock,
    is_hunter,
    is_land_druid,
    is_lore_bard,
    is_open_hand_monk,
    is_thief,
    resolve_colossus_slayer,
    resolve_cutting_words,
    resolve_lands_aid,
    resolve_natural_recovery,
    resolve_open_hand_technique,
    resolve_peerless_skill,
    resolve_wholeness_of_body,
    toggle_dragon_wings,
    trigger_dark_ones_blessing,
)
from combat.utils import calculate_ability_check


class SubclassSpecializationTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='subclass_tester', password='password123')
        self.client.force_authenticate(user=self.user)

        self.fighter_class, _ = CharacterClass.objects.get_or_create(
            name='fighter',
            defaults={'hit_dice': 'd10', 'primary_ability': 'STR'}
        )
        self.ranger_class, _ = CharacterClass.objects.get_or_create(
            name='ranger',
            defaults={'hit_dice': 'd10', 'primary_ability': 'DEX'}
        )
        self.warlock_class, _ = CharacterClass.objects.get_or_create(
            name='warlock',
            defaults={'hit_dice': 'd8', 'primary_ability': 'CHA'}
        )
        self.monk_class, _ = CharacterClass.objects.get_or_create(
            name='monk',
            defaults={'hit_dice': 'd8', 'primary_ability': 'DEX'}
        )
        self.rogue_class, _ = CharacterClass.objects.get_or_create(
            name='rogue',
            defaults={'hit_dice': 'd8', 'primary_ability': 'DEX'}
        )
        self.bard_class, _ = CharacterClass.objects.get_or_create(
            name='bard',
            defaults={'hit_dice': 'd8', 'primary_ability': 'CHA'}
        )
        self.druid_class, _ = CharacterClass.objects.get_or_create(
            name='druid',
            defaults={'hit_dice': 'd8', 'primary_ability': 'WIS'}
        )
        self.sorcerer_class, _ = CharacterClass.objects.get_or_create(
            name='sorcerer',
            defaults={'hit_dice': 'd6', 'primary_ability': 'CHA'}
        )
        self.race, _ = CharacterRace.objects.get_or_create(
            name='human',
            defaults={'size': 'M', 'speed': 30}
        )

        self.prone_cond, _ = Condition.objects.get_or_create(
            name='Prone',
            defaults={'description': 'Prone condition'}
        )

        self.session = CombatSession.objects.create(
            status='active',
            current_round=1,
            current_turn_index=0
        )

    def _create_character(self, name, char_class, level=3, subclass="", stats_dict=None, ruleset='2024'):
        char = Character.objects.create(
            user=self.user,
            name=name,
            level=level,
            character_class=char_class,
            race=self.race,
            subclass=subclass,
            ruleset_version=ruleset
        )
        defaults = {
            'strength': 16,
            'dexterity': 14,
            'constitution': 14,
            'intelligence': 10,
            'wisdom': 14,
            'charisma': 14,
            'armor_class': 15,
            'max_hit_points': 30,
            'hit_points': 30
        }
        if stats_dict:
            defaults.update(stats_dict)
        CharacterStats.objects.create(character=char, **defaults)
        return char

    def _create_participant(self, name, p_type='character', character=None, hp=30, max_hp=30, ac=15, feature_uses=None):
        return CombatParticipant.objects.create(
            combat_session=self.session,
            name=name,
            participant_type=p_type,
            character=character,
            current_hp=hp,
            max_hp=max_hp,
            armor_class=ac,
            initiative=15,
            position_x=10,
            position_y=10,
            is_active=True,
            feature_uses=feature_uses or {}
        )

    # -----------------------------------------------------------------------
    # 1. Fighter — Champion
    # -----------------------------------------------------------------------

    def test_champion_detection_and_critical_threshold(self):
        """Champion Fighter gets 19-20 at lvl 3+, 18-20 at lvl 15+."""
        champ_char = self._create_character('Valerius', self.fighter_class, level=3, subclass='Champion')
        champ_p = self._create_participant('Valerius', character=champ_char)

        self.assertTrue(champ_p.is_champion())
        self.assertEqual(champ_p.get_critical_threshold(), 19)

        # Level 15 Champion: Superior Critical (18-20)
        champ_char.level = 15
        champ_char.save()
        self.assertEqual(champ_p.get_critical_threshold(), 18)

    def test_champion_improved_critical_attack_hit_and_auto_hit(self):
        """Natural 19 roll hits high AC as an automatic critical hit."""
        champ_char = self._create_character('Valerius', self.fighter_class, level=3, subclass='Champion')
        champ_p = self._create_participant('Valerius', character=champ_char)
        # Enemy with impossible AC 35
        target = self._create_participant('Iron Golem', p_type='enemy', ac=35, hp=50, max_hp=50)

        url = f"/api/combat/sessions/{self.session.id}/attack/"
        # Mock d20 roll to 19 (natural 19 is critical for Champion)
        with patch('combat.views.combat_action_views.roll_d20', return_value=(19, "d20: 19")):
            response = self.client.post(url, {
                'attacker_id': champ_p.id,
                'target_id': target.id,
                'attack_name': 'Greatsword',
                'damage_string': '2d6+3',
                'is_melee': True
            })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['hit'])
        self.assertTrue(response.data['critical'])
        self.assertIn("Improved Critical", response.data['breakdown']['attack'])

    def test_champion_remarkable_athlete_half_proficiency(self):
        """Champion level 7+ Remarkable Athlete adds ceil(prof / 2) to non-proficient checks."""
        # Level 7 character: proficiency bonus is 3 -> ceil(3 / 2) = 2
        total, breakdown = calculate_ability_check(
            base_roll=10,
            ability_modifier=2,
            proficiency_bonus=3,
            proficiency=False,
            half_proficiency=True
        )
        self.assertEqual(total, 14)  # 10 + 2 + 2
        self.assertIn("Remarkable Athlete: +2", breakdown)

    def test_champion_survivor_regeneration_at_half_hp(self):
        """Level 18 Champion regains 5 + CON HP at start of turn if at half HP or less."""
        champ_char = self._create_character('Valerius', self.fighter_class, level=18, subclass='Champion')
        champ_p = self._create_participant('Valerius', character=champ_char, hp=15, max_hp=100)
        # Con modifier for stats_dict constitution 14 is +2 -> heals 5 + 2 = 7
        healed = apply_champion_survivor(champ_p)
        self.assertEqual(healed, 7)
        self.assertEqual(champ_p.current_hp, 22)

        # Above half HP: does not heal
        champ_p.current_hp = 55
        champ_p.save()
        self.assertEqual(apply_champion_survivor(champ_p), 0)

        # At 0 HP: does not heal
        champ_p.current_hp = 0
        champ_p.save()
        self.assertEqual(apply_champion_survivor(champ_p), 0)

    # -----------------------------------------------------------------------
    # 2. Ranger — Hunter (Colossus Slayer)
    # -----------------------------------------------------------------------

    def test_hunter_colossus_slayer_extra_damage_on_wounded_target(self):
        """Hunter deals extra 1d8 to a wounded creature once per turn."""
        hunter_char = self._create_character('Robin', self.ranger_class, level=3, subclass='Hunter')
        hunter_p = self._create_participant('Robin', character=hunter_char)
        # Target wounded (current 20 < max 30)
        target = self._create_participant('Goblin Chief', p_type='enemy', hp=20, max_hp=30, ac=10)

        url = f"/api/combat/sessions/{self.session.id}/attack/"
        with patch('combat.views.combat_action_views.roll_d20', return_value=(15, "d20: 15")):
            with patch('combat.subclasses.random.randint', return_value=6):
                response = self.client.post(url, {
                    'attacker_id': hunter_p.id,
                    'target_id': target.id,
                    'attack_name': 'Longbow',
                    'damage_string': '1d8+2',
                    'is_melee': False
                })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['hit'])
        self.assertIn("Colossus Slayer (1d8): +6", response.data['breakdown']['damage'])
        hunter_p.refresh_from_db()
        self.assertTrue(hunter_p.feature_uses.get('colossus_slayer_used_this_turn'))

        # Second attack in same turn cannot use Colossus Slayer
        hunter_p.attacks_remaining = 1
        hunter_p.action_used = False
        hunter_p.save()
        with patch('combat.views.combat_action_views.roll_d20', return_value=(15, "d20: 15")):
            response2 = self.client.post(url, {
                'attacker_id': hunter_p.id,
                'target_id': target.id,
                'attack_name': 'Longbow',
                'damage_string': '1d8+2',
                'is_melee': False
            })
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        self.assertNotIn("Colossus Slayer", response2.data['breakdown'].get('damage') or '')

    def test_hunter_colossus_slayer_ignored_on_uninjured_target(self):
        """Target at max HP takes no Colossus Slayer damage."""
        hunter_char = self._create_character('Robin', self.ranger_class, level=3, subclass='Hunter')
        hunter_p = self._create_participant('Robin', character=hunter_char)
        target = self._create_participant('Healthy Orc', p_type='enemy', hp=30, max_hp=30, ac=10)

        url = f"/api/combat/sessions/{self.session.id}/attack/"
        with patch('combat.views.combat_action_views.roll_d20', return_value=(15, "d20: 15")):
            response = self.client.post(url, {
                'attacker_id': hunter_p.id,
                'target_id': target.id,
                'attack_name': 'Longbow',
                'damage_string': '1d8+2',
                'is_melee': False
            })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn("Colossus Slayer", response.data['breakdown'].get('damage') or '')

    # -----------------------------------------------------------------------
    # 3. Warlock — Fiend Patron (Dark One's Blessing)
    # -----------------------------------------------------------------------

    def test_fiend_dark_ones_blessing_grants_temporary_hp_on_kill(self):
        """Downing a hostile enemy grants CHA mod + Warlock level temp HP."""
        # Level 3 warlock, CHA mod +2 -> grants 2 + 3 = 5 temp HP
        fiend_char = self._create_character('Malakor', self.warlock_class, level=3, subclass='Fiend Patron')
        fiend_p = self._create_participant('Malakor', character=fiend_char)
        target = self._create_participant('Skeleton', p_type='enemy', hp=4, max_hp=10, ac=10)

        url = f"/api/combat/sessions/{self.session.id}/attack/"
        with patch('combat.views.combat_action_views.roll_d20', return_value=(15, "d20: 15")):
            with patch('combat.utils.random.randint', return_value=8):
                response = self.client.post(url, {
                    'attacker_id': fiend_p.id,
                    'target_id': target.id,
                    'attack_name': 'Eldritch Blast',
                    'damage_string': '1d10+2',
                    'is_melee': False
                })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("Dark One's Blessing: Gained 5 Temp HP", response.data['breakdown']['damage'])
        fiend_p.refresh_from_db()
        self.assertEqual(fiend_p.temporary_hp, 5)

    def test_fiend_dark_ones_blessing_does_not_overwrite_higher_temp_hp(self):
        """Existing higher temporary HP is preserved."""
        fiend_char = self._create_character('Malakor', self.warlock_class, level=3, subclass='Fiend Patron')
        fiend_p = self._create_participant('Malakor', character=fiend_char)
        fiend_p.temporary_hp = 12
        fiend_p.save()
        target = self._create_participant('Rat', p_type='enemy', hp=1, max_hp=4)
        target.current_hp = 0

        trigger_dark_ones_blessing(fiend_p, target)
        fiend_p.refresh_from_db()
        self.assertEqual(fiend_p.temporary_hp, 12)

    # -----------------------------------------------------------------------
    # 4. Monk — Warrior of the Open Hand
    # -----------------------------------------------------------------------

    def test_open_hand_technique_topple_inflicts_prone_on_failed_save(self):
        """Open Hand Technique (Topple) knocks target Prone on failed DEX save."""
        monk_char = self._create_character('Li', self.monk_class, level=3, subclass='Warrior of the Open Hand')
        monk_p = self._create_participant('Li', character=monk_char, feature_uses={'ki_pool_remaining': 3})
        target = self._create_participant('Hobgoblin', p_type='enemy', hp=20, max_hp=20, ac=10)

        # 1. Activate Flurry of Blows
        url_feat = f"/api/combat/sessions/{self.session.id}/use_feature/"
        res_flurry = self.client.post(url_feat, {
            'participant_id': monk_p.id,
            'feature_name': 'Flurry of Blows'
        })
        self.assertEqual(res_flurry.status_code, status.HTTP_200_OK)
        monk_p.refresh_from_db()
        self.assertEqual(monk_p.feature_uses.get('open_hand_flurry_attacks_remaining'), 2)

        # 2. Strike target with Open Hand Technique Topple
        url_atk = f"/api/combat/sessions/{self.session.id}/attack/"
        with patch('combat.views.combat_action_views.roll_d20', return_value=(15, "d20: 15")):
            # Mock enemy DEX save to roll 2 (fails vs DC 8 + 2 + 2 = 12)
            with patch('combat.subclasses.roll_d20', return_value=(2, "d20: 2")):
                res_atk = self.client.post(url_atk, {
                    'attacker_id': monk_p.id,
                    'target_id': target.id,
                    'attack_name': 'Unarmed Strike',
                    'damage_string': '1d6+2',
                    'is_melee': True,
                    'open_hand_technique': 'topple'
                })

        self.assertEqual(res_atk.status_code, status.HTTP_200_OK)
        self.assertIn("knocked PRONE", res_atk.data['breakdown']['damage'])
        target.refresh_from_db()
        self.assertTrue(target.conditions.filter(name__iexact='Prone').exists())

    def test_open_hand_technique_push_15ft(self):
        """Open Hand Technique (Push) displaces target 15 ft on failed STR save."""
        monk_char = self._create_character('Li', self.monk_class, level=3, subclass='Warrior of the Open Hand')
        monk_p = self._create_participant('Li', character=monk_char)
        monk_p.position_x, monk_p.position_y = 10, 10
        monk_p.save()

        target = self._create_participant('Ogre', p_type='enemy', hp=30, max_hp=30, ac=10)
        target.position_x, target.position_y = 15, 10
        target.save()

        # Failed STR save pushes 15 ft along X axis
        with patch('combat.subclasses.roll_d20', return_value=(1, "d20: 1")):
            res = resolve_open_hand_technique(self.session, monk_p, target, 'push')

        self.assertTrue(res['success'])
        self.assertTrue(res['target_pushed'])
        target.refresh_from_db()
        self.assertEqual(target.position_x, 30)  # 15 + 15 = 30

    def test_open_hand_technique_no_reactions(self):
        """Open Hand Technique (No Reactions) locks enemy reaction until end of next turn."""
        monk_char = self._create_character('Li', self.monk_class, level=3, subclass='Warrior of the Open Hand')
        monk_p = self._create_participant('Li', character=monk_char)
        target = self._create_participant('Mage', p_type='enemy', hp=20, max_hp=20)

        self.assertTrue(target.can_use_reaction())
        res = resolve_open_hand_technique(self.session, monk_p, target, 'no_reactions')
        self.assertTrue(res['success'])
        self.assertTrue(res['target_no_reactions'])
        target.refresh_from_db()
        self.assertFalse(target.can_use_reaction())

    def test_wholeness_of_body_healing_action(self):
        """Open Hand Monk can activate Wholeness of Body to heal HP."""
        monk_char = self._create_character('Li', self.monk_class, level=6, subclass='Warrior of the Open Hand', ruleset='2014')
        monk_p = self._create_participant('Li', character=monk_char, hp=10, max_hp=50)

        url = f"/api/combat/sessions/{self.session.id}/use_feature/"
        response = self.client.post(url, {
            'participant_id': monk_p.id,
            'feature_name': 'Wholeness of Body'
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # 2014 rules: 3 x level 6 = 18 HP healed
        self.assertEqual(response.data['healed'], 18)
        monk_p.refresh_from_db()
        self.assertEqual(monk_p.current_hp, 28)
        self.assertTrue(monk_p.action_used)

        # Cannot use twice before a long rest
        monk_p.action_used = False
        monk_p.attacks_remaining = 2
        monk_p.save()
        res_second = self.client.post(url, {
            'participant_id': monk_p.id,
            'feature_name': 'Wholeness of Body'
        })
        self.assertEqual(res_second.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("No uses of Wholeness of Body remaining", res_second.data['error'])

    # -----------------------------------------------------------------------
    # 5. Rogue — Thief (Fast Hands)
    # -----------------------------------------------------------------------

    def test_thief_fast_hands_use_item_bonus_action(self):
        """Thief Rogue can use a potion as a bonus action without spending their action."""
        thief_char = self._create_character('Shadow', self.rogue_class, level=3, subclass='Thief')
        thief_p = self._create_participant('Shadow', character=thief_char, hp=10, max_hp=30)

        url = f"/api/combat/sessions/{self.session.id}/use_item/"
        response = self.client.post(url, {
            'participant_id': thief_p.id,
            'item_name': 'Potion of Healing',
            'as_bonus_action': True
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        thief_p.refresh_from_db()
        self.assertTrue(thief_p.bonus_action_used)
        self.assertFalse(thief_p.action_used)
        self.assertGreater(thief_p.attacks_remaining, 0)
        self.assertIn("Fast Hands (Bonus Action)", response.data['message'])

    def test_thief_fast_hands_cunning_action(self):
        """Thief Rogue can use Cunning Action with 'Use an Object'."""
        thief_char = self._create_character('Shadow', self.rogue_class, level=3, subclass='Thief')
        thief_p = self._create_participant('Shadow', character=thief_char)

        url = f"/api/combat/sessions/{self.session.id}/use_feature/"
        response = self.client.post(url, {
            'participant_id': thief_p.id,
            'feature_name': 'Cunning Action',
            'subaction': 'use an object'
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("Fast Hands to manipulate an object", response.data['message'])
        thief_p.refresh_from_db()
        self.assertTrue(thief_p.bonus_action_used)

    # -----------------------------------------------------------------------
    # 6. Bard — College of Lore
    # -----------------------------------------------------------------------

    def test_lore_bard_detection_and_inspiration_die_scaling(self):
        """Lore Bard detection and Bardic Inspiration die progression (d6 -> d8 -> d10 -> d12)."""
        bard_char = self._create_character('Orpheus', self.bard_class, level=3, subclass='College of Lore')
        bard_p = self._create_participant('Orpheus', character=bard_char)

        self.assertTrue(bard_p.is_lore_bard())
        self.assertEqual(get_bardic_inspiration_die(bard_p), 6)

        bard_char.level = 5
        bard_char.save()
        self.assertEqual(get_bardic_inspiration_die(bard_p), 8)

        bard_char.level = 10
        bard_char.save()
        self.assertEqual(get_bardic_inspiration_die(bard_p), 10)

        bard_char.level = 15
        bard_char.save()
        self.assertEqual(get_bardic_inspiration_die(bard_p), 12)

    def test_lore_bard_cutting_words_reduces_attack_roll(self):
        """Cutting Words uses reaction, expends inspiration, and reduces enemy attack roll."""
        bard_char = self._create_character('Orpheus', self.bard_class, level=3, subclass='College of Lore')
        bard_p = self._create_participant('Orpheus', character=bard_char, feature_uses={'bardic_inspiration_remaining': 3})
        enemy = self._create_participant('Goblin', p_type='enemy', hp=12, max_hp=12, ac=15)

        with patch('random.randint', return_value=4):
            res = resolve_cutting_words(self.session, bard_p, enemy, roll_type='attack', roll_value=16)

        self.assertTrue(res['success'])
        self.assertEqual(res['reduction'], 4)
        self.assertEqual(res['modified_value'], 12)
        bard_p.refresh_from_db()
        self.assertTrue(bard_p.reaction_used)
        self.assertEqual(bard_p.feature_uses['bardic_inspiration_remaining'], 2)

    def test_lore_bard_cutting_words_charmed_immunity_check(self):
        """Creature immune to charmed cannot be targeted by Cutting Words."""
        bard_char = self._create_character('Orpheus', self.bard_class, level=3, subclass='College of Lore')
        bard_p = self._create_participant('Orpheus', character=bard_char)
        enemy = self._create_participant('Golem', p_type='enemy')
        # Golem has protection buff making it charm immune
        enemy.feature_uses = {'active_buffs': [{'name': 'Protection from Evil and Good'}]}
        enemy.save()

        can_use, reason = can_use_cutting_words(bard_p, enemy)
        self.assertFalse(can_use)
        self.assertIn("immune to being charmed", reason)

    def test_lore_bard_peerless_skill(self):
        """Peerless Skill adds Bardic Inspiration die to an ability check at level 14+."""
        bard_char = self._create_character('Orpheus', self.bard_class, level=14, subclass='College of Lore')
        bard_p = self._create_participant('Orpheus', character=bard_char, feature_uses={'bardic_inspiration_remaining': 2})

        with patch('random.randint', return_value=7):
            new_tot, annot = resolve_peerless_skill(bard_p, check_total=12)

        self.assertEqual(new_tot, 19)
        self.assertIn("Peerless Skill", annot)
        bard_p.refresh_from_db()
        self.assertEqual(bard_p.feature_uses['bardic_inspiration_remaining'], 1)

    # -----------------------------------------------------------------------
    # 7. Druid — Circle of the Land
    # -----------------------------------------------------------------------

    def test_land_druid_detection_and_natural_recovery(self):
        """Land Druid recovers spell slots up to half druid level (round up)."""
        druid_char = self._create_character('Sylva', self.druid_class, level=5, subclass='Circle of the Land')
        druid_char.stats.expended_spell_slots = {'1': 2, '2': 1, '3': 1}
        druid_char.stats.save()
        druid_p = self._create_participant('Sylva', character=druid_char)

        self.assertTrue(druid_p.is_land_druid())
        self.assertEqual(get_natural_recovery_limit(druid_p), 3)  # ceil(5/2) = 3

        # Recover one 2nd-level slot and one 1st-level slot (total 3 levels)
        res = resolve_natural_recovery(druid_p, slots_to_recover={'1': 1, '2': 1})
        self.assertTrue(res['success'])
        druid_char.stats.refresh_from_db()
        self.assertEqual(druid_char.stats.expended_spell_slots['1'], 1)
        self.assertEqual(druid_char.stats.expended_spell_slots['2'], 0)

        # Cannot use twice before long rest
        res_twice = resolve_natural_recovery(druid_p)
        self.assertFalse(res_twice['success'])
        self.assertIn("already been used today", res_twice['message'])

    def test_land_druid_lands_aid_burst(self):
        """Land's Aid damages enemies in 10 ft radius and heals ally."""
        druid_char = self._create_character('Sylva', self.druid_class, level=3, subclass='Circle of the Land')
        druid_p = self._create_participant('Sylva', character=druid_char, feature_uses={'wild_shape_uses': 2})
        druid_p.position_x = 10
        druid_p.position_y = 10
        druid_p.save()

        # Injured ally within 10 ft
        ally = self._create_participant('Wounded Ranger', p_type='character', hp=10, max_hp=30)
        ally.position_x = 15
        ally.position_y = 10
        ally.save()

        # Enemy within 10 ft
        enemy = self._create_participant('Skeleton', p_type='enemy', hp=20, max_hp=20, ac=12)
        enemy.position_x = 12
        enemy.position_y = 10
        enemy.save()

        with patch('random.randint', return_value=4):  # 2d6 = 8 necrotic / heal
            res = resolve_lands_aid(self.session, druid_p, target_x=12, target_y=10, heal_target=ally)

        self.assertTrue(res['success'])
        druid_p.refresh_from_db()
        self.assertEqual(druid_p.feature_uses['wild_shape_uses'], 1)
        self.assertTrue(druid_p.action_used)

        ally.refresh_from_db()
        self.assertGreater(ally.current_hp, 10)
        enemy.refresh_from_db()
        self.assertLess(enemy.current_hp, 20)

    def test_land_druid_lands_stride_and_natures_ward(self):
        """Land's Stride ignores difficult terrain; Nature's Ward provides poison immunity/resistance."""
        druid_char = self._create_character('Sylva', self.druid_class, level=10, subclass='Circle of the Land')
        druid_p = self._create_participant('Sylva', character=druid_char)

        self.assertTrue(has_lands_stride(druid_p))
        self.assertTrue(has_natures_ward(druid_p))
        self.assertTrue(druid_p.has_natures_ward())
        self.assertTrue(druid_p.has_lands_stride())

        # Test poison damage resistance (halved damage)
        old_hp = druid_p.current_hp
        druid_p.take_damage(20, damage_type='poison')
        # 20 damage halved to 10
        self.assertEqual(druid_p.current_hp, old_hp - 10)
        self.assertIsNotNone(druid_p.last_resistance_info)
        self.assertEqual(druid_p.last_resistance_info['source'], "Nature's Ward")

    # -----------------------------------------------------------------------
    # 8. Sorcerer — Draconic Sorcery
    # -----------------------------------------------------------------------

    def test_draconic_sorcerer_elemental_affinity_damage(self):
        """Draconic Sorcerer adds CHA modifier to spells of matching draconic element."""
        sorc_char = self._create_character('Ignis', self.sorcerer_class, level=6, subclass='Draconic Sorcery',
                                           stats_dict={'charisma': 18})
        sorc_p = self._create_participant('Ignis', character=sorc_char,
                                          feature_uses={'dragon_ancestor': 'Red Dragon'})

        self.assertTrue(sorc_p.is_draconic_sorcerer())
        self.assertEqual(get_draconic_ancestor_element(sorc_p), 'fire')

        # Fire spell deals +4 damage (CHA mod 18 = +4)
        bonus, annot = apply_elemental_affinity_damage(sorc_p, 'fire', 20)
        self.assertEqual(bonus, 4)
        self.assertIn("Elemental Affinity", annot)

        # Cold spell does NOT get fire bonus
        no_bonus, _ = apply_elemental_affinity_damage(sorc_p, 'cold', 20)
        self.assertEqual(no_bonus, 0)

    def test_draconic_sorcerer_elemental_affinity_resistance(self):
        """Spend 1 Sorcery Point to gain 1 hour resistance to ancestor damage type."""
        sorc_char = self._create_character('Ignis', self.sorcerer_class, level=6, subclass='Draconic Sorcery')
        sorc_p = self._create_participant('Ignis', character=sorc_char,
                                          feature_uses={'dragon_ancestor': 'Red Dragon', 'sorcery_points': 3})


        res = activate_elemental_affinity_resistance(sorc_p)
        self.assertTrue(res['success'])
        self.assertEqual(res['damage_type'], 'fire')
        self.assertEqual(res['remaining_sorcery_points'], 2)

        self.assertTrue(has_elemental_affinity_resistance(sorc_p, 'fire'))
        self.assertTrue(sorc_p.has_elemental_affinity_resistance('fire'))

        # Incoming fire damage is halved
        old_hp = sorc_p.current_hp
        sorc_p.take_damage(20, damage_type='fire')
        self.assertEqual(sorc_p.current_hp, old_hp - 10)
        self.assertEqual(sorc_p.last_resistance_info['source'], 'Elemental Affinity')

    def test_draconic_sorcerer_dragon_wings(self):
        """Dragon Wings at level 14 grants fly speed equal to walking speed."""
        sorc_char = self._create_character('Ignis', self.sorcerer_class, level=14, subclass='Draconic Sorcery')
        sorc_p = self._create_participant('Ignis', character=sorc_char)

        # Manifest wings
        res = toggle_dragon_wings(sorc_p, manifest=True)
        self.assertTrue(res['success'])
        self.assertTrue(res['manifested'])
        self.assertEqual(res['fly_speed'], 30)

        sorc_p.refresh_from_db()
        self.assertTrue(sorc_p.can_fly())
        self.assertEqual(sorc_p.get_fly_speed(), 30)

        # Dismiss wings
        res_off = toggle_dragon_wings(sorc_p, manifest=False)
        self.assertTrue(res_off['success'])
        self.assertFalse(res_off['manifested'])
        sorc_p.refresh_from_db()
        self.assertFalse(sorc_p.can_fly())

