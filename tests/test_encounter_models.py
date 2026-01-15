"""
Tests for Encounter Theme and Biome Models

Tests the database models for the encounter theme and biome distribution system.
"""
from django.test import TestCase
from django.db import IntegrityError

from encounters.models import (
    EncounterTheme, EnemyThemeAssociation, ThemeIncompatibility,
    BiomeEncounterWeight, Encounter
)
from bestiary.models import Enemy, EnemyStats


class EncounterThemeModelTests(TestCase):
    """Test EncounterTheme model"""
    
    def test_create_theme(self):
        """Test creating an encounter theme"""
        theme = EncounterTheme.objects.create(
            name="Bandit Ambush",
            category="humanoid",
            description="Outlaws and criminals",
            min_cr=1,
            max_cr=8,
            weight=100,
            flavor_text="A band of outlaws..."
        )
        
        self.assertEqual(theme.name, "Bandit Ambush")
        self.assertEqual(theme.category, "humanoid")
        self.assertTrue(theme.min_cr < theme.max_cr)
    
    def test_theme_unique_name(self):
        """Test theme names must be unique"""
        EncounterTheme.objects.create(
            name="Bandit Ambush",
            category="humanoid",
            description="Test"
        )
        
        # Attempt duplicate
        with self.assertRaises(IntegrityError):
            EncounterTheme.objects.create(
                name="Bandit Ambush",  # Duplicate
                category="undead",
                description="Different"
            )
    
    def test_theme_str_representation(self):
        """Test string representation includes category"""
        theme = EncounterTheme.objects.create(
            name="Undead Horde",
            category="undead",
            description="Zombies and skeletons"
        )
        
        self.assertIn("Undead Horde", str(theme))
        self.assertIn("Undead", str(theme))


class EnemyThemeAssociationTests(TestCase):
    """Test EnemyThemeAssociation model"""
    
    def setUp(self):
        self.theme = EncounterTheme.objects.create(
            name="Bandit Ambush",
            category="humanoid",
            description="Outlaws"
        )
        
        self.enemy = Enemy.objects.create(
            name="Bandit",
            creature_type="humanoid",
            challenge_rating="1/8"
        )
        EnemyStats.objects.create(
            enemy=self.enemy,
            hit_points=11,
            armor_class=12
        )
    
    def test_create_association(self):
        """Test linking enemy to theme"""
        assoc = EnemyThemeAssociation.objects.create(
            theme=self.theme,
            enemy=self.enemy,
            role="support",
            weight=100,
            min_count=2,
            max_count=6
        )
        
        self.assertEqual(assoc.theme, self.theme)
        self.assertEqual(assoc.enemy, self.enemy)
        self.assertEqual(assoc.role, "support")
    
    def test_unique_theme_enemy_role(self):
        """Test same enemy can't have same role twice in theme"""
        EnemyThemeAssociation.objects.create(
            theme=self.theme,
            enemy=self.enemy,
            role="support"
        )
        
        # Attempt duplicate
        with self.assertRaises(IntegrityError):
            EnemyThemeAssociation.objects.create(
                theme=self.theme,
                enemy=self.enemy,
                role="support"  # Same role
            )
    
    def test_enemy_multiple_roles(self):
        """Test enemy can have multiple roles in same theme"""
        EnemyThemeAssociation.objects.create(
            theme=self.theme,
            enemy=self.enemy,
            role="support"
        )
        
        # Different role - should work
        assoc2 = EnemyThemeAssociation.objects.create(
            theme=self.theme,
            enemy=self.enemy,
            role="elite"
        )
        
        self.assertEqual(assoc2.role, "elite")


class ThemeIncompatibilityTests(TestCase):
    """Test ThemeIncompatibility model"""
    
    def setUp(self):
        self.bandit_theme = EncounterTheme.objects.create(
            name="Bandit Ambush",
            category="humanoid",
            description="Outlaws"
        )
        
        self.beholder_theme = EncounterTheme.objects.create(
            name="Beholder Lair",
            category="aberration",
            description="Reality-warping horrors"
        )
    
    def test_create_incompatibility(self):
        """Test marking themes as incompatible"""
        incomp = ThemeIncompatibility.objects.create(
            theme1=self.bandit_theme,
            theme2=self.beholder_theme,
            reason="Bandits flee from aberrations",
            allow_chaotic=True
        )
        
        self.assertEqual(incomp.theme1, self.bandit_theme)
        self.assertEqual(incomp.theme2, self.beholder_theme)
        self.assertTrue(incomp.allow_chaotic)
    
    def test_unique_theme_pair(self):
        """Test same theme pair can't be added twice"""
        ThemeIncompatibility.objects.create(
            theme1=self.bandit_theme,
            theme2=self.beholder_theme,
            reason="Test"
        )
        
        # Attempt duplicate
        with self.assertRaises(IntegrityError):
            ThemeIncompatibility.objects.create(
                theme1=self.bandit_theme,
                theme2=self.beholder_theme,
                reason="Different reason"
            )


class BiomeEncounterWeightTests(TestCase):
    """Test BiomeEncounterWeight model"""
    
    def setUp(self):
        self.theme = EncounterTheme.objects.create(
            name="Giant Scorpions",
            category="beast",
            description="Desert predators"
        )
    
    def test_create_endemic_weight(self):
        """Test creating endemic biome weight"""
        weight = BiomeEncounterWeight.objects.create(
            biome="desert",
            theme=self.theme,
            category="endemic",
            weight=100
        )
        
        self.assertEqual(weight.biome, "desert")
        self.assertEqual(weight.category, "endemic")
    
    def test_create_anomaly_weight(self):
        """Test creating anomaly with narrative"""
        weight = BiomeEncounterWeight.objects.create(
            biome="arctic",
            theme=self.theme,
            category="anomaly",
            weight=10,
            narrative_reason="Escaped from a wizard's menagerie"
        )
        
        self.assertEqual(weight.category, "anomaly")
        self.assertTrue(len(weight.narrative_reason) > 0)
    
    def test_unique_biome_theme_category(self):
        """Test same biome/theme/category can't be added twice"""
        BiomeEncounterWeight.objects.create(
            biome="desert",
            theme=self.theme,
            category="endemic"
        )
        
        # Attempt duplicate
        with self.assertRaises(IntegrityError):
            BiomeEncounterWeight.objects.create(
                biome="desert",
                theme=self.theme,
                category="endemic"  # Same combo
            )


class EncounterModelTests(TestCase):
    """Test updated Encounter model with theme/biome support"""
    
    def setUp(self):
        self.theme = EncounterTheme.objects.create(
            name="Bandit Ambush",
            category="humanoid",
            description="Outlaws"
        )
    
    def test_create_themed_encounter(self):
        """Test creating encounter with theme"""
        encounter = Encounter.objects.create(
            name="Forest Ambush",
            theme=self.theme,
            biome="forest",
            is_chaotic=False
        )
        
        self.assertEqual(encounter.theme, self.theme)
        self.assertEqual(encounter.biome, "forest")
        self.assertFalse(encounter.is_chaotic)
    
    def test_create_chaotic_encounter(self):
        """Test creating chaotic encounter with narrative"""
        encounter = Encounter.objects.create(
            name="Strange Encounter",
            biome="desert",
            is_chaotic=True,
            narrative_justification="A magical accident brought these foes together"
        )
        
        self.assertTrue(encounter.is_chaotic)
        self.assertTrue(len(encounter.narrative_justification) > 0)
    
    def test_encounter_without_theme(self):
        """Test encounter can exist without theme (backwards compatibility)"""
        encounter = Encounter.objects.create(
            name="Random Encounter"
        )
        
        self.assertIsNone(encounter.theme)
        self.assertFalse(encounter.is_chaotic)
