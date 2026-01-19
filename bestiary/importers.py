import json
from typing import List, Dict, Optional
from django.conf import settings

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


class DnDBeyondAPI:
    """Integration with D&D Beyond API for monster data"""
    
    BASE_URL = "https://www.dndbeyond.com/api"
    
    def __init__(self, api_key: Optional[str] = None):
        if not REQUESTS_AVAILABLE:
            raise ImportError('Requests library not available. Install with: pip install requests')
        
        self.api_key = api_key or getattr(settings, 'DND_BEYOND_API_KEY', None)
        self.session = requests.Session()
        if self.api_key:
            self.session.headers.update({'Authorization': f'Bearer {self.api_key}'})
    
    def search_monsters(self, query: str, limit: int = 20) -> List[Dict]:
        """Search for monsters by name"""
        try:
            url = f"{self.BASE_URL}/monsters"
            params = {
                'search': query,
                'limit': limit
            }
            
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            return data.get('results', [])
            
        except requests.RequestException as e:
            print(f"D&D Beyond API error: {e}")
            return []
    
    def get_monster_details(self, monster_id: str) -> Optional[Dict]:
        """Get detailed monster information by ID"""
        try:
            url = f"{self.BASE_URL}/monsters/{monster_id}"
            
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            return response.json()
            
        except requests.RequestException as e:
            print(f"D&D Beyond API error: {e}")
            return None
    
    def parse_monster_data(self, dndbeyond_data: Dict) -> Dict:
        """Convert D&D Beyond format to our internal format"""
        try:
            monster = {
                'name': dndbeyond_data.get('name', 'Unknown'),
                'hit_points': dndbeyond_data.get('hitPoints', 1),
                'armor_class': dndbeyond_data.get('armorClass', 10),
                'challenge_rating': dndbeyond_data.get('challengeRating', '1/4'),
                'speed': dndbeyond_data.get('speed', '30 ft.'),
                'darkvision': dndbeyond_data.get('darkvision'),
                'blindsight': dndbeyond_data.get('blindsight'),
                'tremorsense': dndbeyond_data.get('tremorsense'),
                'truesight': dndbeyond_data.get('truesight'),
                'passive_perception': dndbeyond_data.get('passivePerception'),
                'spell_save_dc': dndbeyond_data.get('spellSaveDc'),
                'spell_attack_bonus': dndbeyond_data.get('spellAttackBonus'),
            }
            
            # Parse ability scores
            abilities = dndbeyond_data.get('abilities', {})
            monster.update({
                'strength': abilities.get('strength', 10),
                'dexterity': abilities.get('dexterity', 10),
                'constitution': abilities.get('constitution', 10),
                'intelligence': abilities.get('intelligence', 10),
                'wisdom': abilities.get('wisdom', 10),
                'charisma': abilities.get('charisma', 10),
            })
            
            # Parse saving throws
            saves = dndbeyond_data.get('savingThrows', {})
            monster.update({
                'str_save': saves.get('strength'),
                'dex_save': saves.get('dexterity'),
                'con_save': saves.get('constitution'),
                'int_save': saves.get('intelligence'),
                'wis_save': saves.get('wisdom'),
                'cha_save': saves.get('charisma'),
            })
            
            # Parse skills
            skills = dndbeyond_data.get('skills', {})
            monster.update({
                'athletics': skills.get('athletics'),
                'acrobatics': skills.get('acrobatics'),
                'sleight_of_hand': skills.get('sleightOfHand'),
                'stealth': skills.get('stealth'),
                'arcana': skills.get('arcana'),
                'history': skills.get('history'),
                'investigation': skills.get('investigation'),
                'nature': skills.get('nature'),
                'religion': skills.get('religion'),
                'animal_handling': skills.get('animalHandling'),
                'insight': skills.get('insight'),
                'medicine': skills.get('medicine'),
                'perception': skills.get('perception'),
                'survival': skills.get('survival'),
                'deception': skills.get('deception'),
                'intimidation': skills.get('intimidation'),
                'performance': skills.get('performance'),
                'persuasion': skills.get('persuasion'),
            })
            
            # Parse attacks
            attacks = []
            for attack_data in dndbeyond_data.get('attacks', []):
                attacks.append({
                    'name': attack_data.get('name', 'Attack'),
                    'bonus': attack_data.get('bonus', 0),
                    'damage': attack_data.get('damage', '1d4')
                })
            monster['attacks'] = attacks
            
            # Parse abilities
            abilities_list = []
            for ability_data in dndbeyond_data.get('abilities', []):
                abilities_list.append({
                    'name': ability_data.get('name', 'Ability'),
                    'description': ability_data.get('description', '')
                })
            monster['abilities'] = abilities_list
            
            # Parse spells
            spells = []
            for spell_data in dndbeyond_data.get('spells', []):
                spell = {
                    'name': spell_data.get('name', 'Spell'),
                    'save_dc': spell_data.get('saveDc')
                }
                
                # Parse spell slots
                slots = []
                for slot_data in spell_data.get('slots', []):
                    slots.append({
                        'level': slot_data.get('level', 1),
                        'uses': slot_data.get('uses', 1)
                    })
                spell['slots'] = slots
                spells.append(spell)
            monster['spells'] = spells
            
            # Parse resistances
            resistances = []
            for res_data in dndbeyond_data.get('resistances', []):
                resistances.append({
                    'damage_type': res_data.get('damageType', ''),
                    'resistance_type': res_data.get('type', 'resistance'),
                    'notes': res_data.get('notes', '')
                })
            monster['resistances'] = resistances
            
            # Parse languages
            monster['languages'] = dndbeyond_data.get('languages', [])
            
            return monster
            
        except Exception as e:
            print(f"Error parsing D&D Beyond data: {e}")
            return {}
    
    def get_monster_by_name(self, name: str) -> Optional[Dict]:
        """Get a specific monster by name"""
        results = self.search_monsters(name, limit=1)
        if results:
            monster_id = results[0].get('id')
            if monster_id:
                return self.get_monster_details(monster_id)
        return None


class Open5eAPI:
    """Integration with Open5e API for monster data"""
    
    BASE_URL = "https://api.open5e.com/monsters/"
    
    def __init__(self):
        if not REQUESTS_AVAILABLE:
            raise ImportError('Requests library not available. Install with: pip install requests')
        self.session = requests.Session()
    
    def get_all_monsters(self, limit: int = 50) -> List[Dict]:
        """Fetch all monsters from Open5e API, handling pagination"""
        monsters = []
        next_url = f"{self.BASE_URL}?limit={limit}"
        
        while next_url:
            try:
                print(f"Fetching {next_url}...")
                response = self.session.get(next_url, timeout=30)
                response.raise_for_status()
                data = response.json()
                
                monsters.extend(data.get('results', []))
                next_url = data.get('next')
                
            except requests.RequestException as e:
                print(f"Open5e API error: {e}")
                break
                
        return monsters

    def parse_monster_data(self, data: Dict) -> Dict:
        """Convert Open5e format to our internal format"""
        # Mapping Open5e fields to our model
        monster = {
            'name': data.get('name', 'Unknown'),
            'hit_points': data.get('hit_points', 1),
            'armor_class': data.get('armor_class', 10),
            'challenge_rating': str(data.get('challenge_rating', '')),
            'speed': self._format_speed(data.get('speed', {})),
            'strength': data.get('strength', 10),
            'dexterity': data.get('dexterity', 10),
            'constitution': data.get('constitution', 10),
            'intelligence': data.get('intelligence', 10),
            'wisdom': data.get('wisdom', 10),
            'charisma': data.get('charisma', 10),
            'str_save': data.get('strength_save'),
            'dex_save': data.get('dexterity_save'),
            'con_save': data.get('constitution_save'),
            'int_save': data.get('intelligence_save'),
            'wis_save': data.get('wisdom_save'),
            'cha_save': data.get('charisma_save'),
            'perception': data.get('skills', {}).get('perception'), # Simplified skill extraction
            'stealth': data.get('skills', {}).get('stealth'),
            # ... other skills would need more robust parsing if needed
            'darkvision': data.get('senses', '').split(',')[0] if 'darkvision' in data.get('senses', '') else None,
            'passive_perception': data.get('perception'), # Open5e has explicit field often
            'languages': data.get('languages', '').split(', '),
        }
        
        # Attacks
        attacks = []
        for action in (data.get('actions') or []):
            if 'attack_bonus' in action:
                 attacks.append({
                    'name': action.get('name'),
                    'bonus': action.get('attack_bonus', 0),
                    'damage': action.get('damage_dice', '1d4') # Simplification, logic is complex
                })
        monster['attacks'] = attacks

        # Abilities (Special Abilities)
        abilities = []
        for ability in (data.get('special_abilities') or []):
            abilities.append({
                'name': ability.get('name'),
                'description': ability.get('desc')
            })
        monster['abilities'] = abilities
        
        return monster

    def _format_speed(self, speed_data):
        if isinstance(speed_data, dict):
            return ', '.join([f"{k} {v}" for k, v in speed_data.items()])
        return str(speed_data)

class SRDMonsterData:
    """Official D&D 5e SRD monster data"""
    
    @staticmethod
    def get_srd_monsters() -> List[Dict]:
        """Get official SRD monster data"""
        return [
            {
                'name': 'Goblin',
                'hit_points': 7,
                'armor_class': 15,
                'challenge_rating': '1/4',
                'strength': 8,
                'dexterity': 14,
                'constitution': 10,
                'intelligence': 10,
                'wisdom': 8,
                'charisma': 8,
                'speed': '30 ft.',
                'darkvision': '60 ft.',
                'passive_perception': 9,
                'stealth': 6,
                'attacks': [
                    {
                        'name': 'Scimitar',
                        'bonus': 4,
                        'damage': '1d6+2 slashing'
                    },
                    {
                        'name': 'Shortbow',
                        'bonus': 4,
                        'damage': '1d6+2 piercing'
                    }
                ],
                'abilities': [
                    {
                        'name': 'Nimble Escape',
                        'description': 'The goblin can take the Disengage or Hide action as a bonus action on each of its turns.'
                    }
                ],
                'resistances': [],
                'languages': ['Common', 'Goblin']
            },
            {
                'name': 'Orc',
                'hit_points': 15,
                'armor_class': 13,
                'challenge_rating': '1/2',
                'strength': 16,
                'dexterity': 12,
                'constitution': 16,
                'intelligence': 7,
                'wisdom': 11,
                'charisma': 10,
                'speed': '30 ft.',
                'darkvision': '60 ft.',
                'passive_perception': 10,
                'intimidation': 2,
                'attacks': [
                    {
                        'name': 'Greataxe',
                        'bonus': 5,
                        'damage': '1d12+3 slashing'
                    },
                    {
                        'name': 'Javelin',
                        'bonus': 5,
                        'damage': '1d6+3 piercing'
                    }
                ],
                'abilities': [
                    {
                        'name': 'Aggressive',
                        'description': 'As a bonus action, the orc can move up to its speed toward a hostile creature that it can see.'
                    }
                ],
                'resistances': [],
                'languages': ['Common', 'Orc']
            },
            {
                'name': 'Kobold',
                'hit_points': 5,
                'armor_class': 12,
                'challenge_rating': '1/8',
                'strength': 7,
                'dexterity': 15,
                'constitution': 9,
                'intelligence': 8,
                'wisdom': 7,
                'charisma': 8,
                'speed': '30 ft.',
                'darkvision': '60 ft.',
                'passive_perception': 8,
                'attacks': [
                    {
                        'name': 'Dagger',
                        'bonus': 4,
                        'damage': '1d4+2 piercing'
                    }
                ],
                'abilities': [
                    {
                        'name': 'Pack Tactics',
                        'description': 'The kobold has advantage on an attack roll against a creature if at least one of the kobold\'s allies is within 5 feet of the creature and the ally isn\'t incapacitated.'
                    }
                ],
                'resistances': [],
                'languages': ['Common', 'Draconic']
            },
            {
                'name': 'Skeleton',
                'hit_points': 13,
                'armor_class': 13,
                'challenge_rating': '1/4',
                'strength': 10,
                'dexterity': 14,
                'constitution': 15,
                'intelligence': 6,
                'wisdom': 8,
                'charisma': 5,
                'speed': '30 ft.',
                'passive_perception': 9,
                'attacks': [
                    {
                        'name': 'Shortsword',
                        'bonus': 4,
                        'damage': '1d6+2 piercing'
                    }
                ],
                'abilities': [],
                'resistances': [
                    {
                        'damage_type': 'Bludgeoning',
                        'resistance_type': 'vulnerability'
                    }
                ],
                'languages': []
            },
            {
                'name': 'Zombie',
                'hit_points': 22,
                'armor_class': 8,
                'challenge_rating': '1/4',
                'strength': 13,
                'dexterity': 6,
                'constitution': 16,
                'intelligence': 3,
                'wisdom': 6,
                'charisma': 1,
                'speed': '20 ft.',
                'passive_perception': 8,
                'attacks': [
                    {
                        'name': 'Slam',
                        'bonus': 3,
                        'damage': '1d6+1 bludgeoning'
                    }
                ],
                'abilities': [
                    {
                        'name': 'Undead Fortitude',
                        'description': 'If damage reduces the zombie to 0 hit points, it must make a Constitution saving throw with a DC of 5 + the damage taken, unless the damage is radiant or from a critical hit. On a success, the zombie drops to 1 hit point instead.'
                    }
                ],
                'resistances': [],
                'languages': []
            }
        ]
