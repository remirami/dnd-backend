from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIRequestFactory

from bestiary.models import Enemy, EnemyStats
from characters.models import Character, CharacterClass, CharacterRace, CharacterStats
from combat.models import CombatParticipant, CombatSession
from combat.views.session_views import CombatSessionViewSet
from items.models import DamageType, Weapon


class ClassFeaturesCombatTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user(username='barbarian_tester', password='password123')
        self.session = CombatSession.objects.create(status='active', current_round=1, current_turn_index=0)

        # Damage types
        self.slashing, _ = DamageType.objects.get_or_create(name='Slashing')
        self.fire, _ = DamageType.objects.get_or_create(name='Fire')

        # Barbarian Character
        self.barb_class = CharacterClass.objects.create(name='barbarian', hit_dice='d12', primary_ability='STR')
        self.race = CharacterRace.objects.create(name='human', size='M', speed=30)
        self.barb = Character.objects.create(
            name='Conan', user=self.user, level=3, character_class=self.barb_class, race=self.race
        )
        CharacterStats.objects.create(
            character=self.barb, hit_points=35, max_hit_points=35, armor_class=14, strength=16, dexterity=14, constitution=16
        )

        self.barb_p = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='character',
            character=self.barb,
            current_hp=35,
            max_hp=35,
            armor_class=14,
            initiative=20
        )

        # Enemy
        self.orc = Enemy.objects.create(name='Orc Berserker', hp=30, ac=13, challenge_rating='1')
        EnemyStats.objects.create(
            enemy=self.orc, strength=16, dexterity=12, constitution=16, intelligence=7, wisdom=11, charisma=10,
            hit_points=30, armor_class=13
        )
        self.orc_p = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='enemy',
            name='Orc Berserker',
            current_hp=30,
            max_hp=30,
            armor_class=13,
            initiative=10
        )

    def test_barbarian_rage_activation_and_damage_resistance(self):
        """Entering Rage grants resistance to Slashing damage (half damage)."""
        view = CombatSessionViewSet.as_view({'post': 'use_feature'})
        request = self.factory.post(
            f'/combat/sessions/{self.session.id}/use_feature/',
            {'participant_id': self.barb_p.id, 'feature_name': 'Rage'},
            format='json'
        )
        response = view(request, pk=self.session.id)
        self.assertEqual(response.status_code, 200)

        self.barb_p.refresh_from_db()
        self.assertTrue(self.barb_p.is_raging())
        self.assertTrue(self.barb_p.bonus_action_used)
        self.assertEqual(self.barb_p.get_rage_uses_remaining(), 2)  # Level 3 Barbarian starts with 3, uses 1 -> 2 left

        # Test physical damage resistance (20 Slashing damage -> 10 taken)
        new_hp, _ = self.barb_p.take_damage(20, damage_type=self.slashing)
        self.assertEqual(new_hp, 25)

        # Test non-physical damage (not resisted, 10 Fire damage -> 10 taken)
        new_hp, _ = self.barb_p.take_damage(10, damage_type=self.fire)
        self.assertEqual(new_hp, 15)

    def test_barbarian_reckless_attack_activation(self):
        """Barbarian can activate Reckless Attack on their turn."""
        view = CombatSessionViewSet.as_view({'post': 'use_feature'})
        request = self.factory.post(
            f'/combat/sessions/{self.session.id}/use_feature/',
            {'participant_id': self.barb_p.id, 'feature_name': 'Reckless Attack'},
            format='json'
        )
        response = view(request, pk=self.session.id)
        self.assertEqual(response.status_code, 200)

        self.barb_p.refresh_from_db()
        self.assertTrue(self.barb_p.feature_uses.get('reckless_attack_active'))

    def test_fighter_action_surge(self):
        """Fighter can use Action Surge to recover an action on their turn."""
        fighter_class = CharacterClass.objects.create(name='fighter', hit_dice='d10', primary_ability='STR')
        fighter = Character.objects.create(
            name='Arthur', user=self.user, level=2, character_class=fighter_class, race=self.race
        )
        CharacterStats.objects.create(
            character=fighter, hit_points=20, max_hit_points=20, armor_class=16, strength=16, dexterity=12
        )
        fighter_p = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='character',
            character=fighter,
            current_hp=20,
            max_hp=20,
            armor_class=16,
            initiative=15,
            action_used=True,
            attacks_remaining=0
        )

        view = CombatSessionViewSet.as_view({'post': 'use_feature'})
        request = self.factory.post(
            f'/combat/sessions/{self.session.id}/use_feature/',
            {'participant_id': fighter_p.id, 'feature_name': 'Action Surge'},
            format='json'
        )
        response = view(request, pk=self.session.id)
        self.assertEqual(response.status_code, 200)

        fighter_p.refresh_from_db()
        self.assertFalse(fighter_p.action_used)
        self.assertGreater(fighter_p.attacks_remaining, 0)
        self.assertTrue(fighter_p.feature_uses.get('action_surge_used'))

        # Second attempt should fail (1/rest)
        request2 = self.factory.post(
            f'/combat/sessions/{self.session.id}/use_feature/',
            {'participant_id': fighter_p.id, 'feature_name': 'Action Surge'},
            format='json'
        )
        response2 = view(request2, pk=self.session.id)
        self.assertEqual(response2.status_code, 400)

    def test_cleric_turn_undead_and_damage_end(self):
        """Cleric Turn Undead turns undead on failed WIS save, and taking damage breaks the turned condition."""
        cleric_class = CharacterClass.objects.create(name='cleric', hit_dice='d8', primary_ability='WIS')
        cleric = Character.objects.create(
            name='Caduceus', user=self.user, level=3, character_class=cleric_class, race=self.race
        )
        CharacterStats.objects.create(
            character=cleric, hit_points=24, max_hit_points=24, armor_class=16, wisdom=16, dexterity=10
        )
        cleric_p = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='character',
            character=cleric,
            current_hp=24,
            max_hp=24,
            armor_class=16,
            initiative=14
        )

        # Zombie (undead, CR 1/4)
        zombie = Enemy.objects.create(name='Zombie Minion', hp=22, ac=8, challenge_rating='1/4', creature_type='undead')
        EnemyStats.objects.create(
            enemy=zombie, strength=13, dexterity=6, constitution=16, intelligence=3, wisdom=6, charisma=5,
            hit_points=22, armor_class=8
        )
        zombie_p = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='enemy',
            name='Zombie Minion',
            current_hp=22,
            max_hp=22,
            armor_class=8,
            initiative=5
        )

        view = CombatSessionViewSet.as_view({'post': 'use_feature'})
        request = self.factory.post(
            f'/combat/sessions/{self.session.id}/use_feature/',
            {'participant_id': cleric_p.id, 'feature_name': 'Turn Undead'},
            format='json'
        )
        response = view(request, pk=self.session.id)
        self.assertEqual(response.status_code, 200)

        cleric_p.refresh_from_db()
        self.assertTrue(cleric_p.action_used)
        self.assertEqual(cleric_p.feature_uses.get('channel_divinity_uses_remaining'), 0)

        zombie_p.refresh_from_db()
        # Zombie has -2 WIS mod vs DC 13, if turned:
        if zombie_p.feature_uses.get('is_turned'):
            self.assertTrue(zombie_p.conditions.filter(name__iexact='frightened').exists())
            # Taking damage ends the turned effect!
            zombie_p.take_damage(5, damage_type='slashing')
            zombie_p.refresh_from_db()
            self.assertFalse(zombie_p.feature_uses.get('is_turned', False))
            self.assertFalse(zombie_p.conditions.filter(name__iexact='frightened').exists())

    def test_cleric_destroy_undead(self):
        """Level 5+ Cleric destroys CR <= 0.5 Undead on failed save."""
        cleric_class, _ = CharacterClass.objects.get_or_create(name='cleric', defaults={'hit_dice': 'd8', 'primary_ability': 'WIS'})
        cleric = Character.objects.create(
            name='Jareth', user=self.user, level=5, character_class=cleric_class, race=self.race
        )
        CharacterStats.objects.create(
            character=cleric, hit_points=38, max_hit_points=38, armor_class=18, wisdom=18, dexterity=10
        )
        cleric_p = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='character',
            character=cleric,
            current_hp=38,
            max_hp=38,
            armor_class=18,
            initiative=16
        )

        skeleton = Enemy.objects.create(name='Skeleton Minion', hp=13, ac=13, challenge_rating='1/4', creature_type='undead')
        EnemyStats.objects.create(
            enemy=skeleton, strength=10, dexterity=14, constitution=15, intelligence=6, wisdom=8, charisma=5,
            hit_points=13, armor_class=13
        )
        skel_p = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='enemy',
            name='Skeleton Minion',
            current_hp=13,
            max_hp=13,
            armor_class=13,
            initiative=8
        )

        # Force roll to fail save to test destroy threshold
        import unittest.mock as mock
        with mock.patch('random.randint', return_value=1):
            view = CombatSessionViewSet.as_view({'post': 'use_feature'})
            request = self.factory.post(
                f'/combat/sessions/{self.session.id}/use_feature/',
                {'participant_id': cleric_p.id, 'feature_name': 'Turn Undead'},
                format='json'
            )
            response = view(request, pk=self.session.id)
            self.assertEqual(response.status_code, 200)

        skel_p.refresh_from_db()
        self.assertEqual(skel_p.current_hp, 0)
        self.assertFalse(skel_p.is_active)

    def test_monk_ki_flurry_of_blows_and_stunning_strike(self):
        """Monk can use Ki for Flurry of Blows and Stunning Strike."""
        monk_class = CharacterClass.objects.create(name='monk', hit_dice='d8', primary_ability='DEX')
        monk = Character.objects.create(
            name='Lee', user=self.user, level=5, character_class=monk_class, race=self.race
        )
        CharacterStats.objects.create(
            character=monk, hit_points=35, max_hit_points=35, armor_class=16, dexterity=16, wisdom=16
        )
        monk_p = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='character',
            character=monk,
            current_hp=35,
            max_hp=35,
            armor_class=16,
            initiative=18
        )

        view = CombatSessionViewSet.as_view({'post': 'use_feature'})

        # Flurry of Blows (costs 1 Ki, gives +2 attacks)
        req1 = self.factory.post(
            f'/combat/sessions/{self.session.id}/use_feature/',
            {'participant_id': monk_p.id, 'feature_name': 'Flurry of Blows'},
            format='json'
        )
        res1 = view(req1, pk=self.session.id)
        self.assertEqual(res1.status_code, 200)
        monk_p.refresh_from_db()
        self.assertEqual(monk_p.feature_uses.get('ki_pool_remaining'), 4)
        self.assertEqual(monk_p.attacks_remaining, 4)  # 2 from Extra Attack (Level 5) + 2 from Flurry of Blows

        # Stunning Strike on enemy (costs 1 Ki)
        import unittest.mock as mock
        with mock.patch('random.randint', return_value=1):
            req2 = self.factory.post(
                f'/combat/sessions/{self.session.id}/use_feature/',
                {'participant_id': monk_p.id, 'target_id': self.orc_p.id, 'feature_name': 'Stunning Strike'},
                format='json'
            )
            res2 = view(req2, pk=self.session.id)
            self.assertEqual(res2.status_code, 200)

        monk_p.refresh_from_db()
        self.assertEqual(monk_p.feature_uses.get('ki_pool_remaining'), 3)
        self.orc_p.refresh_from_db()
        self.assertTrue(self.orc_p.conditions.filter(name__iexact='stunned').exists())

    def test_druid_wild_shape_transformation_and_reversion(self):
        """Druid Wild Shape changes HP/AC, and reverting or excess damage restores original HP."""
        druid_class = CharacterClass.objects.create(name='druid', hit_dice='d8', primary_ability='WIS')
        druid = Character.objects.create(
            name='Keyleth', user=self.user, level=3, character_class=druid_class, race=self.race
        )
        CharacterStats.objects.create(
            character=druid, hit_points=25, max_hit_points=25, armor_class=14, wisdom=16
        )
        druid_p = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='character',
            character=druid,
            current_hp=25,
            max_hp=25,
            armor_class=14,
            initiative=12
        )

        view = CombatSessionViewSet.as_view({'post': 'use_feature'})
        # Enter Wild Shape as Wolf
        req1 = self.factory.post(
            f'/combat/sessions/{self.session.id}/use_feature/',
            {'participant_id': druid_p.id, 'feature_name': 'Wild Shape', 'beast_name': 'Wolf'},
            format='json'
        )
        res1 = view(req1, pk=self.session.id)
        self.assertEqual(res1.status_code, 200)

        druid_p.refresh_from_db()
        self.assertTrue(druid_p.feature_uses.get('wild_shaped'))
        self.assertEqual(druid_p.current_hp, 11)  # Wolf HP
        self.assertEqual(druid_p.armor_class, 13)  # Wolf AC

        # Take 15 damage (11 destroys Wolf form, 4 carries over to original 25 HP -> 21 HP)
        druid_p.take_damage(15, damage_type='slashing')
        druid_p.refresh_from_db()
        self.assertFalse(druid_p.feature_uses.get('wild_shaped'))
        self.assertEqual(druid_p.current_hp, 21)
        self.assertEqual(druid_p.armor_class, 14)

    def test_paladin_divine_smite(self):
        """Paladin expends a spell slot on hit to deal radiant smite damage."""
        from characters.models import CharacterItem
        paladin_class, _ = CharacterClass.objects.get_or_create(name='paladin', defaults={'hit_dice': 'd10', 'primary_ability': 'STR'})
        paladin = Character.objects.create(
            name='Uther', user=self.user, level=3, character_class=paladin_class, race=self.race
        )
        paladin_stats = CharacterStats.objects.create(
            character=paladin, hit_points=28, max_hit_points=28, armor_class=18, strength=16, charisma=14,
            spell_slots={'1': 3}, expended_spell_slots={}
        )
        paladin_p = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='character',
            character=paladin,
            current_hp=28,
            max_hp=28,
            armor_class=18,
            initiative=99
        )

        longsword = Weapon.objects.create(name='Longsword', weapon_type='martial_melee', damage_dice='1d8')
        CharacterItem.objects.create(character=paladin, item=longsword, is_equipped=True, equipment_slot='main_hand')

        view = CombatSessionViewSet.as_view({'post': 'attack'})
        import unittest.mock as mock
        with mock.patch('random.randint', side_effect=lambda a, b: 8 if b == 8 else (10 if b == 20 else 4)):
            req = self.factory.post(
                f'/combat/sessions/{self.session.id}/attack/',
                {
                    'attacker_id': paladin_p.id,
                    'target_id': self.orc_p.id,
                    'attack_name': 'Longsword',
                    'smite_slot_level': 1
                },
                format='json'
            )
            res = view(req, pk=self.session.id)
            self.assertEqual(res.status_code, 200)

        paladin_stats.refresh_from_db()
        self.assertEqual(paladin_stats.expended_spell_slots.get('1'), 1)  # Expended 1 slot
        self.assertIn('Divine Smite', res.data.get('message', ''))

    def test_rogue_sneak_attack(self):
        """Rogue deals extra Sneak Attack damage when attacking with advantage."""
        from characters.models import CharacterItem
        rogue_class, _ = CharacterClass.objects.get_or_create(name='rogue', defaults={'hit_dice': 'd6', 'primary_ability': 'DEX'})
        rogue = Character.objects.create(
            name='Vax', user=self.user, level=3, character_class=rogue_class, race=self.race
        )
        CharacterStats.objects.create(
            character=rogue, hit_points=21, max_hit_points=21, armor_class=15, dexterity=18
        )
        rogue_p = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='character',
            character=rogue,
            current_hp=21,
            max_hp=21,
            armor_class=15,
            initiative=99
        )

        dagger = Weapon.objects.create(name='Dagger', weapon_type='simple_melee', damage_dice='1d4', finesse=True)
        CharacterItem.objects.create(character=rogue, item=dagger, is_equipped=True, equipment_slot='main_hand')

        view = CombatSessionViewSet.as_view({'post': 'attack'})
        import unittest.mock as mock
        # Mock d20 attack roll = 15 (hits AC 13), damage dice = 4
        with mock.patch('random.randint', side_effect=lambda a, b: 15 if b == 20 else 4):
            req = self.factory.post(
                f'/combat/sessions/{self.session.id}/attack/',
                {
                    'attacker_id': rogue_p.id,
                    'target_id': self.orc_p.id,
                    'attack_name': 'Dagger',
                    'advantage': True,
                    'dm_override': True,
                    'use_sneak_attack': True
                },
                format='json'
            )
            res = view(req, pk=self.session.id)
            self.assertEqual(res.status_code, 200)

        rogue_p.refresh_from_db()
        self.assertTrue(rogue_p.feature_uses.get('sneak_attack_used_this_turn'))
        self.assertIn('Sneak Attack', res.data.get('message', ''))

    def test_wizard_arcane_recovery(self):
        """Wizard can recover expended spell slots using Arcane Recovery (ceil(level / 2) slot levels)."""
        wiz_class = CharacterClass.objects.create(name='wizard', hit_dice='d6', primary_ability='INT')
        wizard = Character.objects.create(
            name='Elminster', user=self.user, level=3, character_class=wiz_class, race=self.race
        )
        stats = CharacterStats.objects.create(
            character=wizard, hit_points=18, max_hit_points=18, armor_class=12, intelligence=16,
            spell_slots={'1': 4, '2': 2},
            expended_spell_slots={'1': 2, '2': 1}
        )
        wiz_p = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='character',
            character=wizard,
            current_hp=18,
            max_hp=18,
            armor_class=12,
            initiative=15
        )

        view = CombatSessionViewSet.as_view({'post': 'use_feature'})
        # Level 3 Wizard -> max recoverable levels is ceil(3/2) = 2
        # Choose to recover two 1st-level slots: {"1": 2}
        req = self.factory.post(
            f'/combat/sessions/{self.session.id}/use_feature/',
            {
                'participant_id': wiz_p.id,
                'feature_name': 'Arcane Recovery',
                'recovered_slots': {'1': 2}
            },
            format='json'
        )
        res = view(req, pk=self.session.id)
        self.assertEqual(res.status_code, 200, res.data)
        self.assertIn('Arcane Recovery', res.data.get('message', ''))

        stats.refresh_from_db()
        self.assertEqual(stats.expended_spell_slots.get('1'), 0)
        self.assertEqual(stats.expended_spell_slots.get('2'), 1)

        wiz_p.refresh_from_db()
        self.assertTrue(wiz_p.feature_uses.get('arcane_recovery_used'))
        self.assertTrue(wiz_p.action_used)

        # Attempting again in the same combat must fail (already expended)
        wiz_p.action_used = False
        wiz_p.attacks_remaining = 1
        wiz_p.save()
        req2 = self.factory.post(
            f'/combat/sessions/{self.session.id}/use_feature/',
            {
                'participant_id': wiz_p.id,
                'feature_name': 'Arcane Recovery',
                'recovered_slots': {'2': 1}
            },
            format='json'
        )
        res2 = view(req2, pk=self.session.id)
        self.assertEqual(res2.status_code, 400)
        self.assertIn('already expended', res2.data.get('error', ''))

    def test_thunderwave_push_and_range_allowance(self):
        """Thunderwave Self (15-foot cube) allows targets within blast and pushes 10 ft away on failed save."""
        wiz_class = CharacterClass.objects.create(name='wizard', hit_dice='d6', primary_ability='INT')
        wizard = Character.objects.create(
            name='Raistlin', user=self.user, level=3, character_class=wiz_class, race=self.race
        )
        CharacterStats.objects.create(
            character=wizard, hit_points=20, max_hit_points=20, armor_class=12, intelligence=16,
            spell_slots={'1': 4}, expended_spell_slots={'1': 0}
        )
        from characters.models import CharacterSpell
        CharacterSpell.objects.create(character=wizard, name='Thunderwave', level=1, is_prepared=True)
        wiz_p = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='character',
            character=wizard,
            current_hp=20,
            max_hp=20,
            armor_class=12,
            initiative=100,
            position_x=10,
            position_y=10
        )
        # Enemy is at position_x=25, position_y=10 (15 ft away, right at the edge of the 15-ft cube)
        target_p = CombatParticipant.objects.create(
            combat_session=self.session,
            participant_type='enemy',
            name='Goblin Raider',
            current_hp=15,
            max_hp=15,
            armor_class=12,
            initiative=10,
            position_x=25,
            position_y=10
        )

        view = CombatSessionViewSet.as_view({'post': 'cast_spell'})
        import unittest.mock as mock
        # Mock d20 save roll = 1 (fails CON save), damage rolls = 4
        with mock.patch('random.randint', side_effect=lambda a, b: 1 if b == 20 else 4):
            req = self.factory.post(
                f'/combat/sessions/{self.session.id}/cast_spell/',
                {
                    'caster_id': wiz_p.id,
                    'target_ids': [target_p.id],
                    'spell_name': 'Thunderwave',
                    'spell_level': 1,
                    'save_type': 'CON',
                    'save_dc': 13,
                    'damage_string': '2d8',
                    'dm_override': True
                },
                format='json'
            )
            res = view(req, pk=self.session.id)
            self.assertEqual(res.status_code, 200, res.data)

        target_p.refresh_from_db()
        # Should be pushed 10 ft along x away from caster (from x=25 to x=35)
        self.assertEqual(target_p.position_x, 35)
        self.assertEqual(target_p.position_y, 10)
        self.assertIn('blasted 10 ft away', res.data.get('message', ''))


