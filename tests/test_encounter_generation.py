"""
Tests for Encounter Generation Services

Tests the encounter and biome generation logic, including distribution percentages
"""
from django.test import TestCase

from encounters.models import (
    EncounterTheme, EnemyThemeAssociation, ThemeIncompatibility,
    BiomeEncounterWeight, Encounter
)
from encounters.services import EncounterGenerator, BiomeEncounterGenerator
from bestiary.models import Enemy, EnemyStats


class EncounterGeneratorTests(TestCase):
    """Test EncounterGenerator service"""
    
    def setUp(self):
        self.generator = EncounterGenerator()
        
        # Create a test theme
        self.theme = EncounterTheme.objects.create(
            name="Bandit Ambush",
            category="humanoid",
            description="Outlaws and criminals",
            min_cr=1,
            max_cr=8
        )
        
        # Create test enemies
        self.bandit = Enemy.objects.create(
            name="Bandit",
            creature_type="humanoid",
            challenge_rating="1/8"
        )
        EnemyStats.objects.create(
            enemy=self.bandit,
            hit_points=11,
            armor_class=12
        )
        
        self.captain = Enemy.objects.create(
            name="Bandit Captain",
            creature_type="humanoid",
            challenge_rating="2"
        )
        EnemyStats.objects.create(
            enemy=self.captain,
            hit_points=65,
            armor_class=15
        )
        
        # Associate enemies with theme
        EnemyThemeAssociation.objects.create(
            theme=self.theme,
            enemy=self.captain,
            role="leader",
            min_count=1,
            max_count=1
        )
        
        EnemyThemeAssociation.objects.create(
            theme=self.theme,
            enemy=self.bandit,
            role="support",
            min_count=2,
            max_count=6
        )
    
    def test_generate_themed_encounter(self):
        """Test generating a normal themed encounter"""
        encounter = self.generator.generate_encounter(
            party_level=5,
            party_size=4,
            difficulty='medium',
            force_theme=self.theme,
            allow_chaotic=False
        )
        
        self.assertIsNotNone(encounter)
        self.assertEqual(encounter.theme, self.theme)
        self.assertFalse(encounter.is_chaotic)
        self.assertTrue(encounter.enemies.count() > 0)
    
    def test_xp_budget_calculation(self):
        """Test XP budget is calculated correctly"""
        xp_budget = self.generator._calculate_xp_budget(
            party_level=5,
            party_size=4,
            difficulty='hard'
        )
        
        # Level 5, hard difficulty = 750 XP per player
        expected = 750 * 4
        self.assertEqual(xp_budget, expected)
    
    def test_cr_to_float_conversion(self):
        """Test CR string to float conversion"""
        self.assertEqual(self.generator._cr_to_float("1/4"), 0.25)
        self.assertEqual(self.generator._cr_to_float("1/2"), 0.5)
        self.assertEqual(self.generator._cr_to_float("5"), 5.0)
    
    def test_cr_to_xp_mapping(self):
        """Test CR to XP conversion"""
        self.assertEqual(self.generator._cr_to_xp(0.25), 50)
        self.assertEqual(self.generator._cr_to_xp(1), 200)
        self.assertEqual(self.generator._cr_to_xp(5), 1800)
    
    def test_themed_encounter_has_enemies(self):
        """Test themed encounter includes enemies from theme"""
        encounter = self.generator.generate_encounter(
            party_level=5,
            party_size=4,
            force_theme=self.theme,
            allow_chaotic=False
        )
        
        enemy_names = [e.enemy.name for e in encounter.enemies.all()]
        
        # Should include bandits and/or captain
        self.assertTrue(
            'Bandit' in enemy_names or 'Bandit Captain' in enemy_names
        )
    
    def test_chaotic_encounter_generation(self):
        """Test chaotic encounters can be generated"""
        # Force chaotic
        encounter = self.generator._generate_chaotic_encounter(
            party_level=5,
            party_size=4,
            difficulty='medium'
        )
        
        self.assertTrue(encounter.is_chaotic)
        self.assertTrue(len(encounter.narrative_justification) > 0)


class BiomeEncounterGeneratorTests(TestCase):
    """Test BiomeEncounterGenerator service"""
    
    def setUp(self):
        self.biome_generator = BiomeEncounterGenerator()
        
        # Create desert theme
        self.desert_theme = EncounterTheme.objects.create(
            name="Desert Scorpions",
            category="beast",
            description="Giant scorpions",
            min_cr=1,
            max_cr=5
        )
        
        # Create enemy
        self.scorpion = Enemy.objects.create(
            name="Giant Scorpion",
            creature_type="beast",
            challenge_rating="3"
        )
        EnemyStats.objects.create(
            enemy=self.scorpion,
            hit_points=52,
            armor_class=15
        )
        
        # Associate with theme
        EnemyThemeAssociation.objects.create(
            theme=self.desert_theme,
            enemy=self.scorpion,
            role="primary",
            min_count=1,
            max_count=3
        )
        
        # Create biome weight (endemic)
        BiomeEncounterWeight.objects.create(
            biome="desert",
            theme=self.desert_theme,
            category="endemic",
            weight=100
        )
    
    def test_category_distribution_statistics(self):
        """Test category rolls follow 60/20/15/5 distribution"""
        stats = self.biome_generator.get_distribution_stats('desert', num_samples=10000)
        
        # Verify percentages (with 2% tolerance)
        self.assertAlmostEqual(stats['endemic'], 60, delta=2)
        self.assertAlmostEqual(stats['adapted'], 20, delta=2)
        self.assertAlmostEqual(stats['traveler'], 15, delta=2)
        self.assertAlmostEqual(stats['anomaly'], 5, delta=2)
    
    def test_generate_endemic_encounter(self):
        """Test generating endemic encounter for biome"""
        encounter = self.biome_generator.generate_by_biome(
            biome='desert',
            party_level=3,
            party_size=4,
            force_category='endemic'
        )
        
        self.assertEqual(encounter.biome, 'desert')
        self.assertEqual(encounter.theme, self.desert_theme)
    
    def test_forced_category(self):
        """Test forcing specific category works"""
        encounter = self.biome_generator.generate_by_biome(
            biome='desert',
            party_level=3,
            party_size=4,
            force_category='anomaly'
        )
        
        # Should generate even if no anomaly weights exist
        self.assertIsNotNone(encounter)


class EncounterIntegrationTests(TestCase):
    """Integration tests for full encounter generation flow"""
    
    def setUp(self):
        # Create multiple themes
        self.bandit_theme = EncounterTheme.objects.create(
            name="Bandit Ambush",
            category="humanoid",
            description="Outlaws",
            min_cr=1,
            max_cr=8
        )
        
        self.beast_theme = EncounterTheme.objects.create(
            name="Wolf Pack",
            category="beast",
            description="Hungry wolves",
            min_cr=1,
            max_cr=5
        )
        
        # Create enemies for both
        self.bandit = Enemy.objects.create(
            name="Bandit",
            creature_type="humanoid",
            challenge_rating="1/8"
        )
        EnemyStats.objects.create(enemy=self.bandit, hit_points=11, armor_class=12)
        
        self.wolf = Enemy.objects.create(
            name="Wolf",
            creature_type="beast",
            challenge_rating="1/4"
        )
        EnemyStats.objects.create(enemy=self.wolf, hit_points=11, armor_class=13)
        
        # Associate
        EnemyThemeAssociation.objects.create(
            theme=self.bandit_theme,
            enemy=self.bandit,
            role="support"
        )
        EnemyThemeAssociation.objects.create(
            theme=self.beast_theme,
            enemy=self.wolf,
            role="support"
        )
        
        # Biome weights
        BiomeEncounterWeight.objects.create(
            biome='forest',
            theme=self.beast_theme,
            category='endemic',
            weight=100
        )
        BiomeEncounterWeight.objects.create(
            biome='forest',
            theme=self.bandit_theme,
            category='adapted',
            weight=50
        )
    
    def test_full_biome_generation_flow(self):
        """Test complete flow from biome to encounter"""
        generator = BiomeEncounterGenerator()
        
        encounter = generator.generate_by_biome(
            biome='forest',
            party_level=2,
            party_size=4
        )
        
        self.assertEqual(encounter.biome, 'forest')
        self.assertIn(encounter.theme, [self.beast_theme, self.bandit_theme])
        self.assertTrue(encounter.enemies.count() > 0)
