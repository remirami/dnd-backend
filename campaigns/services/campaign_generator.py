"""
Campaign Generator Service

Generates complete gauntlet campaigns with progressive difficulty
and boss encounters
"""
from django.db import transaction

from campaigns.models import Campaign, CampaignEncounter
from campaigns.boss_encounters import get_random_boss_for_biome
from encounters.models import Encounter, EncounterEnemy
from encounters.services import BiomeEncounterGenerator
from bestiary.models import Enemy


class CampaignGenerator:
    """Generate gauntlet campaigns with biome-specific boss encounters"""
    
    def generate_gauntlet(self, biome, party_level, party_size, 
                         encounter_count=5, owner=None, name=None):
        """
        Generate a complete gauntlet campaign
        
        Args:
            biome: Biome type (forest, desert, etc.)
            party_level: Starting character level (1-20)
            party_size: Number of characters (1-4)
            encounter_count: Regular encounters before boss (default 5)
            owner: User who owns the campaign
            name: Optional custom name
            
        Returns:
            Campaign object with all encounters generated
        """
        with transaction.atomic():
            # Create campaign
            campaign_name = name or f"{biome.title()} Gauntlet - Level {party_level}"
            
            campaign = Campaign.objects.create(
                name=campaign_name,
                description=f"Face {encounter_count} challenges and defeat the {biome} boss!",
                biome=biome,
                starting_level=party_level,
                starting_party_size=party_size,
                default_encounter_count=encounter_count,
                owner=owner
            )
            
            # Generate regular encounters
            biome_gen = BiomeEncounterGenerator()
            
            for i in range(encounter_count):
                # Progressive difficulty
                difficulty = self._get_difficulty_for_encounter(i, encounter_count)
                
                # Generate encounter
                encounter = biome_gen.generate_by_biome(
                    biome=biome,
                    party_level=party_level,
                    party_size=party_size,
                    difficulty=difficulty
                )
                
                # Add to campaign
                CampaignEncounter.objects.create(
                    campaign=campaign,
                    encounter=encounter,
                    encounter_number=i + 1,
                    is_boss=False
                )
            
            # Generate boss encounter
            boss_encounter, boss_loot = self._generate_boss_encounter(
                biome, party_level, party_size
            )
            
            CampaignEncounter.objects.create(
                campaign=campaign,
                encounter=boss_encounter,
                encounter_number=encounter_count + 1,
                is_boss=True,
                boss_loot_table=boss_loot
            )
            
            # Update total encounters
            campaign.total_encounters = campaign.campaign_encounters.count()
            campaign.save()
            
            return campaign
    
    def _get_difficulty_for_encounter(self, encounter_index, total_encounters):
        """
        Calculate progressive difficulty curve
        
        Encounter 1: Easy (warm-up)
        Encounter 2-3: Medium
        Encounter 4: Hard
        Encounter 5+: Deadly
        """
        if encounter_index == 0:
            return 'easy'
        elif encounter_index < total_encounters // 2:
            return 'medium'
        elif encounter_index < total_encounters - 1:
            return 'hard'
        else:
            return 'deadly'
    
    def _generate_boss_encounter(self, biome, party_level, party_size):
        """
        Generate biome-specific boss encounter with minions
        
        Returns:
            tuple: (Encounter object, boss_loot_table dict)
        """
        # Get random boss for this biome
        boss_data = get_random_boss_for_biome(biome)
        
        # Find boss enemy in database
        boss_enemy = Enemy.objects.filter(
            name__icontains=boss_data['boss_enemy_name']
        ).first()
        
        if not boss_enemy:
            # Fallback: Find any high-CR enemy
            boss_enemy = Enemy.objects.filter(
                creature_type__in=['dragon', 'giant', 'aberration', 'fiend']
            ).order_by('-challenge_rating').first()
            
            if not boss_enemy:
                # Last resort: any enemy
                boss_enemy = Enemy.objects.first()
        
        # Create boss encounter
        encounter = Encounter.objects.create(
            name=boss_data['name'],
            description=boss_data['flavor_text'],
            biome=biome
        )
        
        # Add boss
        boss_hp = boss_enemy.stats.hit_points if hasattr(boss_enemy, 'stats') else 100
        EncounterEnemy.objects.create(
            encounter=encounter,
            enemy=boss_enemy,
            name=boss_data['name'],
            current_hp=boss_hp
        )
        
        # Add minions (scaled by party size)
        minion_count = min(party_size, 3)  # Max 3 minions
        for i, minion_name in enumerate(boss_data['minions'][:minion_count]):
            minion = Enemy.objects.filter(
                name__icontains=minion_name
            ).first()
            
            if minion:
                minion_hp = minion.stats.hit_points if hasattr(minion, 'stats') else 20
                EncounterEnemy.objects.create(
                    encounter=encounter,
                    enemy=minion,
                    name=f"{minion.name} {i+1}" if minion_count > 1 else minion.name,
                    current_hp=minion_hp
                )
        
        # Return encounter and loot table
        return encounter, boss_data['loot']
