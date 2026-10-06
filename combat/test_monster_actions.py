from django.test import TestCase
from django.contrib.auth.models import User

from bestiary.models import Condition, DamageType, Enemy, EnemyAction, EnemyActionDamage, EnemyTrait
from characters.models import Character, CharacterClass, CharacterRace, CharacterStats
from combat.models import CombatParticipant, CombatSession


class MonsterActionsCombatTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='tester', password='password123')
        self.session = CombatSession.objects.create(status='active', current_round=1, current_turn_index=0)

        # Create Condition
        self.prone_condition, _ = Condition.objects.get_or_create(name='prone')
        self.fire_dmg, _ = DamageType.objects.get_or_create(name='fire')
        self.piercing_dmg, _ = DamageType.objects.get_or_create(name='piercing')

        # Create Reference Data
        self.char_class = CharacterClass.objects.create(
            name='fighter', hit_dice='d10', primary_ability='STR', saving_throw_proficiencies='STR,CON'
        )
        self.race = CharacterRace.objects.create(name='human', size='M', speed=30)

        # Create Player Character
        self.character = Character.objects.create(
            name='Hero', user=self.user, level=3, character_class=self.char_class, race=self.race
        )
        CharacterStats.objects.create(
            character=self.character,
            hit_points=30,
            max_hit_points=30,
            armor_class=14,
            strength=14,
            dexterity=14,
            constitution=14,
            intelligence=10,
            wisdom=10,
            charisma=10
        )
        self.char_participant = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='character',
            character=self.character,
            current_hp=30,
            max_hp=30,
            armor_class=14,
            initiative=10
        )

        # Create Dragon Enemy with Breath Weapon
        self.dragon = Enemy.objects.create(name='Red Dragon', hp=100, ac=18, challenge_rating='10')
        self.breath_action = EnemyAction.objects.create(
            enemy=self.dragon,
            name='Fire Breath (Recharge 5-6)',
            attack_type='saving_throw',
            saving_throw_dc=15,
            saving_throw_ability='DEX',
            half_damage_on_save=True,
            has_recharge=True,
            recharge_min_roll=5
        )
        EnemyActionDamage.objects.create(
            action=self.breath_action,
            dice_count=2,
            dice_sides=6,
            damage_bonus=4,
            damage_type=self.fire_dmg
        )

        self.dragon_participant = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='enemy',
            name='Red Dragon',
            current_hp=100,
            max_hp=100,
            armor_class=18,
            initiative=15
        )

    def test_recharge_state_initialization(self):
        """CombatParticipant should automatically initialize recharge_state with all recharge abilities ready."""
        self.assertIn('Fire Breath (Recharge 5-6)', self.dragon_participant.recharge_state)
        self.assertTrue(self.dragon_participant.recharge_state['Fire Breath (Recharge 5-6)'])

    def test_saving_throw_breath_weapon_via_attack_endpoint(self):
        """Calling attack with a saving_throw action should roll target saving throw and deal damage."""
        from rest_framework.test import APIRequestFactory
        from combat.views.combat_action_views import CombatActionMixin
        from combat.views.session_views import CombatSessionViewSet

        factory = APIRequestFactory()
        request = factory.post(
            f'/api/combat/sessions/{self.session.id}/attack/',
            {
                'attacker_id': self.dragon_participant.id,
                'target_id': self.char_participant.id,
                'attack_name': 'Fire Breath (Recharge 5-6)'
            },
            format='json'
        )
        view = CombatSessionViewSet.as_view({'post': 'attack'})
        response = view(request, pk=self.session.id)

        self.assertEqual(response.status_code, 200)
        self.assertIn('saving_throw', response.data)
        self.assertIn('damage', response.data)
        self.dragon_participant.refresh_from_db()
        # Should now be discharged
        self.assertFalse(self.dragon_participant.recharge_state['Fire Breath (Recharge 5-6)'])

        # Reset turn attacks remaining to test recharge lockout
        self.dragon_participant.attacks_remaining = 1
        self.dragon_participant.action_used = False
        self.dragon_participant.save()

        # Attempting to fire again while discharged should return 400
        request2 = factory.post(
            f'/api/combat/sessions/{self.session.id}/attack/',
            {
                'attacker_id': self.dragon_participant.id,
                'target_id': self.char_participant.id,
                'attack_name': 'Fire Breath (Recharge 5-6)'
            },
            format='json'
        )
        response2 = view(request2, pk=self.session.id)
        self.assertEqual(response2.status_code, 400)
        self.assertIn('recharging', response2.data['error'])

    def test_recharge_check_on_turn_reset(self):
        """check_recharges should roll d6 and recharge if roll >= min_roll."""
        self.dragon_participant.recharge_state['Fire Breath (Recharge 5-6)'] = False
        self.dragon_participant.save()

        # Mock random.randint to return 6 (success)
        import unittest.mock as mock
        with mock.patch('random.randint', return_value=6):
            recharged = self.dragon_participant.check_recharges()
            self.assertIn('Fire Breath (Recharge 5-6)', recharged)
            self.assertTrue(self.dragon_participant.recharge_state['Fire Breath (Recharge 5-6)'])

    def test_pack_tactics_advantage(self):
        """Enemy with Pack Tactics trait should have has_trait('pack_tactics') == True."""
        wolf = Enemy.objects.create(name='Dire Wolf', hp=37, ac=14, challenge_rating='1')
        EnemyTrait.objects.create(enemy=wolf, name='Pack Tactics', trait_type='pack_tactics')
        wolf_p = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='enemy',
            name='Dire Wolf',
            current_hp=37,
            max_hp=37,
            armor_class=14,
            initiative=12
        )
        self.assertTrue(wolf_p.has_trait('pack_tactics'))
        self.assertFalse(self.dragon_participant.has_trait('pack_tactics'))

    def test_character_attack_unarmed_succeeds(self):
        """Player character attack without weapon defaults to Unarmed Strike and succeeds without 500 error."""
        from rest_framework.test import APIRequestFactory
        from combat.views.session_views import CombatSessionViewSet

        # Turn index 1 corresponds to character (initiative 10 vs dragon 15)
        self.session.current_turn_index = 1
        self.session.save()

        factory = APIRequestFactory()
        request = factory.post(
            f'/api/combat/sessions/{self.session.id}/attack/',
            {
                'attacker_id': self.char_participant.id,
                'target_id': self.dragon_participant.id,
            },
            format='json'
        )
        view = CombatSessionViewSet.as_view({'post': 'attack'})
        response = view(request, pk=self.session.id)

        self.assertEqual(response.status_code, 200)
        self.assertIn('attack_roll', response.data)
        self.assertIn('attack_total', response.data)
        # Hero STR=14 (+2 mod), level 3 prof bonus (+2) -> attack modifier should be 4
        from combat.models import CombatAction
        last_action = CombatAction.objects.filter(actor=self.char_participant, action_type='attack').last()
        self.assertIsNotNone(last_action)
        self.assertEqual(last_action.attack_name, 'Unarmed Strike')
        self.assertEqual(last_action.attack_modifier, 4)

    def test_character_attack_with_finesse_weapon(self):
        """Player character with a finesse weapon uses higher of STR or DEX and proper damage dice."""
        from items.models import Weapon
        from characters.models import CharacterItem
        from rest_framework.test import APIRequestFactory
        from combat.views.session_views import CombatSessionViewSet

        # Increase DEX to 16 (+3 mod) so finesse chooses DEX over STR (14, +2)
        char_stats = self.character.stats
        char_stats.dexterity = 16
        char_stats.save()

        rapier = Weapon.objects.create(
            name='Rapier',
            weapon_type='martial_melee',
            damage_dice='1d8',
            finesse=True
        )
        CharacterItem.objects.create(
            character=self.character,
            item=rapier,
            is_equipped=True,
            equipment_slot='main_hand'
        )

        # Set character's turn and reset attacks remaining
        self.session.current_turn_index = 1
        self.session.save()
        self.char_participant.attacks_remaining = 1
        self.char_participant.action_used = False
        self.char_participant.save()

        factory = APIRequestFactory()
        request = factory.post(
            f'/api/combat/sessions/{self.session.id}/attack/',
            {
                'attacker_id': self.char_participant.id,
                'target_id': self.dragon_participant.id,
            },
            format='json'
        )
        view = CombatSessionViewSet.as_view({'post': 'attack'})
        response = view(request, pk=self.session.id)

        self.assertEqual(response.status_code, 200)
        from combat.models import CombatAction
        last_action = CombatAction.objects.filter(actor=self.char_participant, action_type='attack').last()
        self.assertIsNotNone(last_action)
        self.assertEqual(last_action.attack_name, 'Rapier')
        # DEX mod (+3) + prof bonus (+2) = 5
        self.assertEqual(last_action.attack_modifier, 5)

    def test_multi_target_aoe_saving_throw(self):
        """Breath weapons with target_ids should resolve saves and deal damage across multiple targets."""
        from rest_framework.test import APIRequestFactory
        from combat.views.session_views import CombatSessionViewSet
        from combat.models import CombatAction

        # Create a second hero participant
        char2_participant = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='character',
            character=self.character,
            current_hp=25,
            max_hp=25,
            armor_class=14,
            initiative=8,
        )

        self.dragon_participant.attacks_remaining = 1
        self.dragon_participant.action_used = False
        self.dragon_participant.recharge_state = {'Fire Breath (Recharge 5-6)': True}
        self.dragon_participant.save()

        factory = APIRequestFactory()
        request = factory.post(
            f'/api/combat/sessions/{self.session.id}/attack/',
            {
                'attacker_id': self.dragon_participant.id,
                'target_ids': [self.char_participant.id, char2_participant.id],
                'attack_name': 'Fire Breath (Recharge 5-6)',
            },
            format='json'
        )
        view = CombatSessionViewSet.as_view({'post': 'attack'})
        response = view(request, pk=self.session.id)

        self.assertEqual(response.status_code, 200)
        self.assertIn('saving_throw', response.data)
        # Should create a CombatAction entry for each target
        breath_actions = CombatAction.objects.filter(
            actor=self.dragon_participant,
            attack_name='Fire Breath (Recharge 5-6)'
        )
        self.assertGreaterEqual(breath_actions.count(), 2)

        self.dragon_participant.refresh_from_db()
        self.assertFalse(self.dragon_participant.recharge_state['Fire Breath (Recharge 5-6)'])
        self.assertTrue(self.dragon_participant.action_used)

    def test_ai_execute_special_action_action_economy(self):
        """AI special action execution must mark action_used=True and recharge_state[name]=False."""
        from combat.combat_ai import _execute_special_action
        from combat.models import CombatAction

        self.dragon_participant.action_used = False
        self.dragon_participant.attacks_remaining = 1
        self.dragon_participant.recharge_state = {'Fire Breath (Recharge 5-6)': True}
        self.dragon_participant.save()

        res = _execute_special_action(
            self.session,
            self.dragon_participant,
            [self.char_participant],
            self.breath_action
        )
        self.assertEqual(res['type'], 'special_action')

        self.dragon_participant.refresh_from_db()
        self.assertTrue(self.dragon_participant.action_used)
        self.assertEqual(self.dragon_participant.attacks_remaining, 0)
        self.assertFalse(self.dragon_participant.recharge_state['Fire Breath (Recharge 5-6)'])

    def test_recharge_event_logging_on_turn_reset(self):
        """reset_turn should log a CombatAction when a recharge ability becomes available."""
        from combat.models import CombatAction
        import unittest.mock as mock

        self.dragon_participant.recharge_state = {'Fire Breath (Recharge 5-6)': False}
        self.dragon_participant.save()

        with mock.patch('random.randint', return_value=6):
            self.dragon_participant.reset_turn()

        self.dragon_participant.refresh_from_db()
        self.assertTrue(self.dragon_participant.recharge_state['Fire Breath (Recharge 5-6)'])

        recharge_action = CombatAction.objects.filter(
            actor=self.dragon_participant,
            attack_name='Fire Breath (Recharge 5-6)',
            action_type='other'
        ).last()
        self.assertIsNotNone(recharge_action)
        self.assertIn('recharged', recharge_action.description.lower())

    def test_pack_tactics_advantage(self):
        """Wolves with Pack Tactics should gain advantage when an ally is active and engaging."""
        from combat.combat_ai import _check_pack_tactics
        wolf_session = CombatSession.objects.create(status='active', current_round=1, current_turn_index=0)
        hero = CombatParticipant.objects.create(
            combat_session=wolf_session,
            participant_type='character',
            character=self.character,
            current_hp=30,
            max_hp=30,
            armor_class=14,
            initiative=10,
            position_x=0,
            position_y=0
        )
        wolf_enemy = Enemy.objects.create(name='Dire Wolf', hp=37, ac=14, challenge_rating='1')
        EnemyTrait.objects.create(enemy=wolf_enemy, name='Pack Tactics', trait_type='pack_tactics')

        wolf1 = CombatParticipant.objects.create(
            combat_session=wolf_session,
            participant_type='enemy',
            name='Dire Wolf 1',
            current_hp=37,
            max_hp=37,
            armor_class=14,
            initiative=12,
            position_x=5,
            position_y=0
        )
        wolf2 = CombatParticipant.objects.create(
            combat_session=wolf_session,
            participant_type='enemy',
            name='Dire Wolf 2',
            current_hp=37,
            max_hp=37,
            armor_class=14,
            initiative=11,
            position_x=0,
            position_y=5
        )

        # Both wolves active and within 5 ft of hero -> Pack Tactics triggers!
        has_pt = _check_pack_tactics(wolf_session, wolf1, hero)
        self.assertTrue(has_pt)

        # If ally is incapacitated or defeated, Pack Tactics does not trigger
        wolf2.current_hp = 0
        wolf2.is_active = False
        wolf2.save()
        has_pt_solo = _check_pack_tactics(wolf_session, wolf1, hero)
        self.assertFalse(has_pt_solo)

    def test_goblin_nimble_escape_bonus_action(self):
        """Skirmishers with Nimble Escape should use Bonus Action to Disengage when threatened."""
        from combat.combat_ai import resolve_enemy_turn
        goblin_enemy = Enemy.objects.create(name='Goblin', hp=7, ac=15, challenge_rating='1/4')
        EnemyTrait.objects.create(enemy=goblin_enemy, name='Nimble Escape', trait_type='nimble_escape')
        scimitar = EnemyAction.objects.create(
            enemy=goblin_enemy,
            name='Scimitar',
            attack_type='melee_weapon',
            attack_bonus=4
        )
        EnemyActionDamage.objects.create(action=scimitar, dice_count=1, dice_sides=6, damage_bonus=2)

        goblin = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='enemy',
            name='Goblin',
            current_hp=7,
            max_hp=7,
            armor_class=15,
            initiative=14,
            position_x=5,
            position_y=0
        )
        self.char_participant.position_x = 0
        self.char_participant.position_y = 0
        self.char_participant.save()

        actions = resolve_enemy_turn(self.session, goblin)
        goblin.refresh_from_db()

        # Goblin should have attacked and used Bonus Action to Disengage
        self.assertTrue(goblin.action_used)
        self.assertTrue(goblin.bonus_action_used)
        self.assertTrue(goblin.feature_uses.get('disengaged', False))
        nimble_acts = [a for a in actions if a.get('type') == 'nimble_escape']
        self.assertEqual(len(nimble_acts), 1)

    def test_zombie_undead_fortitude(self):
        """Zombie with Undead Fortitude should roll CON save to survive at 1 HP unless radiant or crit."""
        import unittest.mock as mock
        zombie_enemy = Enemy.objects.create(name='Zombie', hp=22, ac=8, challenge_rating='1/4')
        EnemyTrait.objects.create(enemy=zombie_enemy, name='Undead Fortitude', trait_type='undead_fortitude')

        zombie = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='enemy',
            name='Zombie',
            current_hp=5,
            max_hp=22,
            armor_class=8,
            initiative=8
        )

        # 1. Non-radiant lethal damage with successful CON save (e.g. 10 slashing damage, DC 15)
        with mock.patch('combat.utils.roll_d20', return_value=(18, '18')):
            hp, _ = zombie.take_damage(10, damage_type='slashing')
            self.assertEqual(zombie.current_hp, 1)
            self.assertTrue(zombie.is_active)
            self.assertTrue(zombie.last_undead_fortitude_triggered)

        # 2. Lethal radiant damage bypasses Undead Fortitude
        zombie.current_hp = 5
        zombie.is_active = True
        hp, _ = zombie.take_damage(10, damage_type='radiant')
        self.assertEqual(zombie.current_hp, 0)
        self.assertFalse(zombie.is_active)

        # 3. Critical hit bypasses Undead Fortitude
        zombie.current_hp = 5
        zombie.is_active = True
        hp, _ = zombie.take_damage(10, damage_type='slashing', is_critical=True)
        self.assertEqual(zombie.current_hp, 0)
        self.assertFalse(zombie.is_active)

    def test_boss_legendary_resistance(self):
        """Boss with Legendary Resistance should convert a failed save into a success up to 3 times."""
        EnemyTrait.objects.create(enemy=self.dragon, name='Legendary Resistance (3/Day)', trait_type='legendary_resistance')

        # Saving throw DC 18, rolled total 11 (failed)
        used, success, msg = self.dragon_participant.check_legendary_resistance('DEX', 18, 11)
        self.assertTrue(used)
        self.assertTrue(success)
        self.assertIn('Legendary Resistance', msg)

        self.dragon_participant.refresh_from_db()
        self.assertEqual(self.dragon_participant.feature_uses['legendary_resistance_remaining'], 2)

    def test_legendary_action_weaving_on_next_turn(self):
        """When player turn ends, active boss weaves a legendary action before next creature acts."""
        from combat.models import CombatAction
        leg_session = CombatSession.objects.create(status='active', current_round=1, current_turn_index=0)
        hero1 = CombatParticipant.objects.create(
            combat_session=leg_session,
            participant_type='character',
            character=self.character,
            current_hp=30,
            max_hp=30,
            armor_class=14,
            initiative=20,
            position_x=10,
            position_y=10
        )
        hero2 = CombatParticipant.objects.create(
            combat_session=leg_session,
            participant_type='character',
            character=self.character,
            name='Companion',
            current_hp=25,
            max_hp=25,
            armor_class=13,
            initiative=18,
            position_x=10,
            position_y=15
        )
        from bestiary.models import EnemyLegendaryAction
        dragon_enemy = Enemy.objects.create(name='Adult Red Dragon', hp=256, ac=19, challenge_rating='17')
        EnemyLegendaryAction.objects.create(enemy=dragon_enemy, name='Wing Attack', cost=2, description='Beats wings')
        EnemyLegendaryAction.objects.create(enemy=dragon_enemy, name='Tail Attack', cost=1, description='Tail strike')

        dragon_boss = CombatParticipant.objects.create(
            combat_session=leg_session,
            participant_type='enemy',
            name='Adult Red Dragon',
            current_hp=100,
            max_hp=100,
            armor_class=18,
            initiative=12,
            position_x=15,
            position_y=15,
            legendary_actions_max=3,
            legendary_actions_remaining=3
        )

        # Advance turn from hero1 -> dragon boss weaves a legendary action before hero2's turn
        next_p = leg_session.next_turn()
        self.assertEqual(next_p.id, hero2.id)

        dragon_boss.refresh_from_db()
        self.assertLess(dragon_boss.legendary_actions_remaining, 3)

        leg_action = CombatAction.objects.filter(
            combat_session=leg_session,
            actor=dragon_boss,
            is_legendary_action=True
        ).first()
        self.assertIsNotNone(leg_action)
        self.assertIn("LEGENDARY ACTION", leg_action.description)

    def test_shield_spell_defensive_reaction(self):
        """Mage casting Shield as a reaction should gain +5 AC and turn hit into a miss."""
        from combat.combat_ai import _execute_attack
        mage_enemy = Enemy.objects.create(name='Shield Mage', hp=40, ac=12, challenge_rating='6')
        EnemyTrait.objects.create(enemy=mage_enemy, name='Shield Spell', trait_type='shield_spell')

        self.char_participant.position_x = 10
        self.char_participant.position_y = 10
        self.char_participant.save(update_fields=['position_x', 'position_y'])

        mage = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='enemy',
            name='Shield Mage',
            current_hp=40,
            max_hp=40,
            armor_class=12,
            initiative=12,
            position_x=10,
            position_y=15,
            reaction_used=False,
            spell_uses_remaining={'Shield': 2}
        )

        # Hero attacks with total 15 vs AC 12. Shield adds +5 AC (total 17), making 15 a MISS!
        import unittest.mock as mock
        with mock.patch('combat.combat_ai.roll_d20', return_value=(11, '11')):
            attack_data = {'name': 'Longsword', 'bonus': 4, 'damage': '1d8+2 slashing', 'action_obj': None}
            res = _execute_attack(self.session, self.char_participant, mage, attack_data)

            self.assertFalse(res['hit'])
            mage.refresh_from_db()
            self.assertTrue(mage.reaction_used)
            self.assertTrue(mage.feature_uses.get('shield_spell_active', False))

    def test_opportunity_attack_reaction_on_grid_movement(self):
        """Moving out of enemy reach without Disengage triggers an opportunity attack reaction."""
        from rest_framework.test import APIRequestFactory
        from combat.views.session_views import CombatSessionViewSet

        move_session = CombatSession.objects.create(status='active', current_round=1, current_turn_index=0)
        hero = CombatParticipant.objects.create(
            combat_session=move_session,
            participant_type='character',
            character=self.character,
            current_hp=30,
            max_hp=30,
            armor_class=14,
            initiative=20,
            position_x=10,
            position_y=10,
            movement_used=0
        )
        guard = CombatParticipant.objects.create(
            combat_session=move_session,
            participant_type='enemy',
            name='Guard',
            current_hp=20,
            max_hp=20,
            armor_class=15,
            initiative=10,
            position_x=10,
            position_y=15,  # 5 ft away (adjacent)
            reaction_used=False
        )

        # Hero moves from (10, 10) to (10, 0), leaving the 5 ft reach of Guard at (10, 15)
        factory = APIRequestFactory()
        view = CombatSessionViewSet.as_view({'post': 'move'})
        request = factory.post(f'/api/combat/sessions/{move_session.id}/move/', {
            'participant_id': hero.id,
            'target_x': 10,
            'target_y': 0
        }, format='json')
        response = view(request, pk=move_session.id)

        self.assertEqual(response.status_code, 200)
        guard.refresh_from_db()
        self.assertTrue(guard.reaction_used)
        self.assertTrue(any('Opportunity Attack' in str(r.get('description', '')) or r.get('attacker') == 'Guard' for r in response.data.get('opportunity_attacks', [])))

    def test_monster_size_dimensions_and_bounding_box_distance(self):
        """Bounding box distance calculates from nearest edge of multi-square creatures."""
        dragon_enemy = Enemy.objects.create(name='Gargantuan Red Dragon', size='G', hp=300, ac=22)
        dragon = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='enemy',
            name='Gargantuan Red Dragon',
            current_hp=300,
            max_hp=300,
            armor_class=22,
            initiative=15,
            position_x=20,
            position_y=10
        )
        # Gargantuan covers 20x20 ft: X from 20 to 35, Y from 10 to 25
        dim = dragon.get_size_dimensions()
        self.assertEqual(dim['tiles'], 4)
        self.assertEqual(dim['feet'], 20)
        occupied = dragon.get_occupied_cells()
        self.assertEqual(len(occupied), 16)
        self.assertIn((20, 10), occupied)
        self.assertIn((35, 25), occupied)

        # Hero at (15, 10): Hero occupies [15..15]. Dragon occupies [20..35].
        # Distance = 20 - 15 = 5 ft (adjacent to left flank)
        self.char_participant.position_x = 15
        self.char_participant.position_y = 10
        self.char_participant.save(update_fields=['position_x', 'position_y'])

        dist_left = self.char_participant.get_distance_to(dragon)
        self.assertEqual(dist_left, 5)
        self.assertTrue(self.char_participant.is_adjacent_to(dragon))

        # Hero at (40, 10): 20 ft away from dragon's (20, 10) top-left origin,
        # but only 5 ft away from dragon's right flank at X=35!
        self.char_participant.position_x = 40
        self.char_participant.position_y = 10
        self.char_participant.save(update_fields=['position_x', 'position_y'])

        dist_right = self.char_participant.get_distance_to(dragon)
        self.assertEqual(dist_right, 5)
        self.assertTrue(self.char_participant.is_adjacent_to(dragon))

    def test_flying_3d_distance_and_melee_out_of_reach(self):
        """Flying target at 30 ft altitude is out of 5 ft melee weapon reach."""
        from combat.combat_ai import _execute_attack
        flying_enemy = Enemy.objects.create(name='Pteranodon', hp=30, ac=13)
        flyer = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='enemy',
            name='Pteranodon',
            current_hp=30,
            max_hp=30,
            armor_class=13,
            initiative=10,
            position_x=10,
            position_y=10,
            altitude=30,
            is_flying=True
        )
        self.char_participant.position_x = 10
        self.char_participant.position_y = 10
        self.char_participant.altitude = 0
        self.char_participant.save(update_fields=['position_x', 'position_y', 'altitude'])

        # 3D distance is 30 ft (due to altitude)
        dist = self.char_participant.get_distance_to(flyer)
        self.assertEqual(dist, 30)

        # Ground melee attack fails due to reach
        melee_data = {'name': 'Greatsword', 'bonus': 5, 'damage': '2d6+3 slashing', 'action_obj': None}
        res = _execute_attack(self.session, self.char_participant, flyer, melee_data)
        self.assertFalse(res['hit'])
        self.assertTrue(res.get('out_of_range'))

    def test_flying_creature_knocked_prone_falls_and_takes_damage(self):
        """Flying creature knocked prone falls, takes 1d6 per 10 ft, and lands prone on ground."""
        flying_enemy = Enemy.objects.create(name='Wyvern', hp=110, ac=13)
        wyvern = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='enemy',
            name='Wyvern',
            current_hp=100,
            max_hp=110,
            armor_class=13,
            initiative=12,
            altitude=30,
            is_flying=True
        )
        fall_dmg, fall_msg = wyvern.handle_flying_fall(self.session)
        self.assertGreater(fall_dmg, 0)
        self.assertIn("fell 30 ft", fall_msg)
        wyvern.refresh_from_db()
        self.assertEqual(wyvern.altitude, 0)
        self.assertFalse(wyvern.is_flying)
        self.assertTrue(wyvern.conditions.filter(name='prone').exists())

    def test_grapple_size_restriction(self):
        """Grapple endpoint rejects targets more than one size category larger than grappler."""
        from rest_framework.test import APIRequestFactory
        from combat.views.session_views import CombatSessionViewSet

        dragon_enemy = Enemy.objects.create(name='Huge Dragon', size='H', hp=200, ac=18)
        dragon = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='enemy',
            name='Huge Dragon',
            current_hp=200,
            max_hp=200,
            armor_class=18,
            initiative=8,
            position_x=10,
            position_y=15
        )
        # Hero is Medium (rank 2). Huge Dragon is rank 4 (> 2 + 1)
        factory = APIRequestFactory()
        view = CombatSessionViewSet.as_view({'post': 'grapple'})
        request = factory.post(f'/api/combat/sessions/{self.session.id}/grapple/', {
            'grappler_id': self.char_participant.id,
            'target_id': dragon.id
        }, format='json')
        response = view(request, pk=self.session.id)
        self.assertEqual(response.status_code, 400)
        self.assertIn("too large", response.data.get('error', ''))

    def test_bear_multiattack_bite_and_claws(self):
        """Bear with multiattack sequence ['Bite', 'Claw'] executes Bite AND Claws (not two Bites)."""
        from bestiary.models import EnemyMultiattack
        from combat.combat_ai import resolve_enemy_turn

        bear_enemy = Enemy.objects.create(name='Brown Bear', hp=34, ac=11, challenge_rating='1')
        bite = EnemyAction.objects.create(enemy=bear_enemy, name='Bite', attack_type='melee_weapon', attack_bonus=5)
        EnemyActionDamage.objects.create(action=bite, dice_count=1, dice_sides=8, damage_bonus=4)
        claws = EnemyAction.objects.create(enemy=bear_enemy, name='Claws', attack_type='melee_weapon', attack_bonus=5)
        EnemyActionDamage.objects.create(action=claws, dice_count=2, dice_sides=6, damage_bonus=4)

        EnemyMultiattack.objects.create(
            enemy=bear_enemy,
            description="The bear makes two attacks: one with its bite and one with its claws.",
            action_count=2,
            sequence=[{"action_name": "Bite", "count": 1}, {"action_name": "Claw", "count": 1}]
        )

        bear = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='enemy',
            name='Brown Bear',
            current_hp=34,
            max_hp=34,
            armor_class=11,
            initiative=10,
            position_x=5,
            position_y=0
        )
        self.char_participant.position_x = 0
        self.char_participant.position_y = 0
        self.char_participant.save()

        actions = resolve_enemy_turn(self.session, bear)
        attack_actions = [a for a in actions if a.get('type') == 'attack']
        self.assertEqual(len(attack_actions), 2)
        used_action_names = [a.get('action') for a in attack_actions]
        self.assertIn('Bite', used_action_names)
        self.assertIn('Claws', used_action_names)

    def test_bear_multiattack_derived_from_description(self):
        """When sequence is empty, multiattack dynamically derives Bite and Claws from description."""
        from bestiary.models import EnemyMultiattack
        from combat.combat_ai import resolve_enemy_turn

        bear_enemy = Enemy.objects.create(name='Black Bear', hp=19, ac=11, challenge_rating='1/2')
        bite = EnemyAction.objects.create(enemy=bear_enemy, name='Bite', attack_type='melee_weapon', attack_bonus=3)
        EnemyActionDamage.objects.create(action=bite, dice_count=1, dice_sides=6, damage_bonus=2)
        claws = EnemyAction.objects.create(enemy=bear_enemy, name='Claws', attack_type='melee_weapon', attack_bonus=3)
        EnemyActionDamage.objects.create(action=claws, dice_count=2, dice_sides=4, damage_bonus=2)

        EnemyMultiattack.objects.create(
            enemy=bear_enemy,
            description="The bear makes two attacks: one with its bite and one with its claws.",
            action_count=2,
            sequence=[]  # unparsed / empty sequence
        )

        bear = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='enemy',
            name='Black Bear',
            current_hp=19,
            max_hp=19,
            armor_class=11,
            initiative=10,
            position_x=5,
            position_y=0
        )
        self.char_participant.position_x = 0
        self.char_participant.position_y = 0
        self.char_participant.save()

        actions = resolve_enemy_turn(self.session, bear)
        attack_actions = [a for a in actions if a.get('type') == 'attack']
        self.assertEqual(len(attack_actions), 2)
        used_action_names = [a.get('action') for a in attack_actions]
        self.assertIn('Bite', used_action_names)
        self.assertIn('Claws', used_action_names)

    def test_mage_dynamic_spell_cycling_and_cooldown(self):
        """Mage casts Fireball in round 1, then falls back to spell attacks in round 2 due to cooldown."""
        from combat.combat_ai import resolve_enemy_turn

        mage_enemy = Enemy.objects.create(name='Evil Mage', hp=40, ac=12, challenge_rating='6')
        EnemyAction.objects.create(
            enemy=mage_enemy,
            name='Spellcasting',
            attack_type='melee_weapon',
            description=(
                "The mage is a 9th-level spellcaster. Its spellcasting ability is Intelligence "
                "(spell save DC 14, +6 to hit with spell attacks). Prepared spells:\n"
                "* Cantrips: fire bolt, ray of frost\n"
                "* 3rd level: fireball\n"
            )
        )
        EnemyAction.objects.create(
            enemy=mage_enemy,
            name='Dagger',
            attack_type='melee_weapon',
            attack_bonus=5,
            reach_or_range='reach 5 ft.'
        )

        mage = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='enemy',
            name='Evil Mage',
            current_hp=40,
            max_hp=40,
            armor_class=12,
            initiative=12,
            position_x=30,
            position_y=0
        )
        self.char_participant.position_x = 0
        self.char_participant.position_y = 0
        self.char_participant.save()

        # Round 1: Mage unleashes Fireball as special action
        self.session.current_round = 1
        self.session.save()
        actions_r1 = resolve_enemy_turn(self.session, mage)
        special_r1 = [a for a in actions_r1 if a.get('type') == 'special_action']
        self.assertEqual(len(special_r1), 1)
        self.assertEqual(special_r1[0]['action_name'], 'Fireball')

        mage.refresh_from_db()
        cooldowns = mage.feature_uses.get('cooldowns', {})
        self.assertIn('Fireball', cooldowns)
        self.assertGreater(cooldowns['Fireball'], 1)

        # Round 2: Fireball is on cooldown! Mage must NOT cast Fireball, but use spell attack
        self.session.current_round = 2
        self.session.save()
        mage.action_used = False
        mage.attacks_remaining = 1
        mage.save()

        actions_r2 = resolve_enemy_turn(self.session, mage)
        special_r2 = [a for a in actions_r2 if a.get('type') == 'special_action']
        self.assertEqual(len(special_r2), 0)  # Fireball on cooldown!

        attack_r2 = [a for a in actions_r2 if a.get('type') == 'attack']
        self.assertEqual(len(attack_r2), 1)
        used_spell = attack_r2[0].get('action') or attack_r2[0].get('attack_name')
        self.assertIn(used_spell, ['Fire Bolt', 'Ray Of Frost'])

    def test_saving_throw_special_action_simulated_cooldown(self):
        """Monsters with saving throw abilities without recharge enter simulated cooldown instead of spamming."""
        from combat.combat_ai import resolve_enemy_turn

        flayer_enemy = Enemy.objects.create(name='Mind Flayer', hp=71, ac=15, challenge_rating='7')
        mind_blast = EnemyAction.objects.create(
            enemy=flayer_enemy,
            name='Mind Blast',
            attack_type='saving_throw',
            saving_throw_dc=15,
            saving_throw_ability='INT',
            half_damage_on_save=True,
            has_recharge=False  # No explicit recharge
        )
        EnemyActionDamage.objects.create(action=mind_blast, dice_count=4, dice_sides=8, damage_bonus=4)

        tentacles = EnemyAction.objects.create(
            enemy=flayer_enemy,
            name='Tentacles',
            attack_type='melee_weapon',
            attack_bonus=7,
            reach_or_range='reach 5 ft.'
        )
        EnemyActionDamage.objects.create(action=tentacles, dice_count=2, dice_sides=10, damage_bonus=4)

        flayer = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='enemy',
            name='Mind Flayer',
            current_hp=71,
            max_hp=71,
            armor_class=15,
            initiative=15,
            position_x=5,
            position_y=0
        )
        self.char_participant.position_x = 0
        self.char_participant.position_y = 0
        self.char_participant.save()

        # Round 1: Mind Flayer fires Mind Blast
        self.session.current_round = 1
        self.session.save()
        actions_r1 = resolve_enemy_turn(self.session, flayer)
        special_r1 = [a for a in actions_r1 if a.get('type') == 'special_action']
        self.assertEqual(len(special_r1), 1)
        self.assertEqual(special_r1[0]['action_name'], 'Mind Blast')

        flayer.refresh_from_db()
        cooldowns = flayer.feature_uses.get('cooldowns', {})
        self.assertIn('Mind Blast', cooldowns)

        # Round 2: Mind Blast is on simulated cooldown! Flayer attacks with Tentacles
        self.session.current_round = 2
        self.session.save()
        flayer.action_used = False
        flayer.attacks_remaining = 1
        flayer.save()

        actions_r2 = resolve_enemy_turn(self.session, flayer)
        special_r2 = [a for a in actions_r2 if a.get('type') == 'special_action']
        self.assertEqual(len(special_r2), 0)  # Cannot spam Mind Blast!

        attack_r2 = [a for a in actions_r2 if a.get('type') == 'attack']
        self.assertEqual(len(attack_r2), 1)
        self.assertEqual(attack_r2[0].get('action'), 'Tentacles')

