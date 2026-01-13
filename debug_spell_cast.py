"""
Quick test to see the actual spell cast error
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dnd_backend.settings')
django.setup()

from rest_framework.test import APIClient
from combat.models import CombatSession, CombatParticipant
from encounters.models import Encounter, EncounterEnemy
from characters.models import Character, CharacterClass, CharacterRace, CharacterStats, CharacterSpell
from bestiary.models import Enemy, EnemyStats

# Create test data
client = APIClient()

# Create wizard class
character_class = CharacterClass.objects.create(
    name='wizard',
    hit_dice='d6',
    primary_ability='INT',
    saving_throw_proficiencies='INT,WIS'
)

race = CharacterRace.objects.create(
    name='human',
    size='M',
    speed=30
)

# Create wizard character
character = Character.objects.create(
    name='Test Wizard',
    level=5,
    character_class=character_class,
    race=race
)

# Add stats
stats = CharacterStats.objects.create(
    character=character,
    strength=10,
    dexterity=14,
    constitution=14,
    intelligence=18,
    wisdom=12,
    charisma=10,
    hit_points=30,
    max_hit_points=30,
    armor_class=12
)

# Add Fireball spell
spell = CharacterSpell.objects.create(
    character=character,
    name='Fireball',
    level=3,
    school='evocation',
    is_prepared=True
)

print(f"✓ Created wizard: {character.name}")
print(f"✓ Added spell: {spell.name} (prepared={spell.is_prepared})")

# Create enemy
enemy = Enemy.objects.create(
    name='Test Goblin',
    challenge_rating='1/4'
)

enemy_stats = EnemyStats.objects.create(
    enemy=enemy,
    strength=8,
    dexterity=14,
    constitution=10,
    intelligence=10,
    wisdom=8,
    charisma=8,
    hit_points=7,
    armor_class=15
)

# Create encounter
encounter = Encounter.objects.create(
    name='Test Encounter'
)

encounter_enemy = EncounterEnemy.objects.create(
    encounter=encounter,
    enemy=enemy,
    name='Goblin 1',
    current_hp=7,
    initiative=12
)

# Create combat session
combat_session = CombatSession.objects.create(
    encounter=encounter,
    status='active',
    current_round=1,
    current_turn_index=0
)

# Add participants
participant1 = CombatParticipant.objects.create(
    combat_session=combat_session,
    participant_type='character',
    character=character,
    initiative=15,
    current_hp=30,
    max_hp=30,
    armor_class=12
)

participant2 = CombatParticipant.objects.create(
    combat_session=combat_session,
    participant_type='enemy',
    encounter_enemy=encounter_enemy,
    initiative=10,
    current_hp=7,
    max_hp=7,
    armor_class=15
)

print(f"✓ Created combat with participants")
print(f"  - {participant1.get_name()} (initiative={participant1.initiative})")
print(f"  - {participant2.get_name()} (initiative={participant2.initiative})")
print(f"  - Current turn index: {combat_session.current_turn_index}")
print(f"  - Current participant: {combat_session.get_current_participant()}")

# Try to cast spell
response = client.post(
    f'/api/combat/sessions/{combat_session.id}/cast_spell/',
    {
        'caster_id': participant1.id,
        'target_id': participant2.id,
        'spell_name': 'Fireball',
        'spell_level': 3,
        'damage_string': '8d6',
        'save_type': 'DEX',
        'save_dc': 15
    },
    format='json'
)

print(f"\n{'='*60}")
print(f"Response Status: {response.status_code}")
print(f"Response Data: {response.data}")
print(f"{'='*60}")

# Clean up
combat_session.delete()
encounter.delete()
enemy.delete()
character.delete()
character_class.delete()
race.delete()

print("\n✓ Test complete and cleaned up")
