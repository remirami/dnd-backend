from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from combat.models import CombatSession, CombatParticipant, CombatAction, CombatLog
from encounters.models import Encounter, EncounterEnemy
from characters.models import Character, CharacterStats, CharacterClass, CharacterRace
from bestiary.models import Enemy, EnemyStats, DamageType
from combat.utils import roll_d20, calculate_damage


class Command(BaseCommand):
    help = 'Create a test combat session with actions and generate logs'
    
    def handle(self, *args, **options):
        self.stdout.write('Creating test combat data for logging...')
        
        # Get or create character
        character_class, _ = CharacterClass.objects.get_or_create(
            name='fighter',
            defaults={'hit_dice': 'd10', 'primary_ability': 'STR', 'saving_throw_proficiencies': 'STR,CON'}
        )
        race, _ = CharacterRace.objects.get_or_create(
            name='human',
            defaults={'size': 'M', 'speed': 30}
        )
        
        character, created = Character.objects.get_or_create(
            name='Test Warrior',
            defaults={
                'level': 5,
                'character_class': character_class,
                'race': race
            }
        )
        
        if created or not hasattr(character, 'stats'):
            CharacterStats.objects.update_or_create(
                character=character,
                defaults={
                    'strength': 18,
                    'dexterity': 14,
                    'constitution': 16,
                    'intelligence': 10,
                    'wisdom': 12,
                    'charisma': 10,
                    'hit_points': 50,
                    'max_hit_points': 50,
                    'armor_class': 18
                }
            )
            self.stdout.write(f'  Created character: {character.name}')
        else:
            self.stdout.write(f'  Using existing character: {character.name}')
        
        # Get or create enemy
        enemy, created = Enemy.objects.get_or_create(
            name='Test Orc',
            defaults={'challenge_rating': '1/2'}
        )
        
        if created or not hasattr(enemy, 'stats'):
            EnemyStats.objects.update_or_create(
                enemy=enemy,
                defaults={
                    'strength': 16,
                    'dexterity': 12,
                    'constitution': 16,
                    'intelligence': 7,
                    'wisdom': 11,
                    'charisma': 10,
                    'hit_points': 15,
                    'armor_class': 13
                }
            )
            self.stdout.write(f'  Created enemy: {enemy.name}')
        else:
            self.stdout.write(f'  Using existing enemy: {enemy.name}')
        
        # Get or create damage type
        slashing, _ = DamageType.objects.get_or_create(name='Slashing')
        
        # Create encounter
        encounter, created = Encounter.objects.get_or_create(
            name='Test Combat for Logging',
            defaults={'description': 'A test encounter for combat logging'}
        )
        
        if created:
            self.stdout.write(f'  Created encounter: {encounter.name}')
        
        # Create encounter enemy
        encounter_enemy, created = EncounterEnemy.objects.get_or_create(
            encounter=encounter,
            enemy=enemy,
            defaults={'name': 'Orc Warrior', 'current_hp': 15}
        )
        
        # Create combat session
        session, created = CombatSession.objects.get_or_create(
            encounter=encounter,
            status='preparing',
            defaults={'started_at': timezone.now() - timedelta(minutes=30)}
        )
        
        if created:
            self.stdout.write(f'  Created combat session: {session.id}')
        else:
            # Clear existing participants and actions
            session.participants.all().delete()
            session.actions.all().delete()
            self.stdout.write(f'  Using existing session: {session.id}')
        
        # Add participants
        char_participant, _ = CombatParticipant.objects.get_or_create(
            combat_session=session,
            character=character,
            defaults={
                'participant_type': 'character',
                'initiative': 15,
                'current_hp': 50,
                'max_hp': 50,
                'armor_class': 18
            }
        )
        session.participants.add(char_participant)
        
        enemy_participant, _ = CombatParticipant.objects.get_or_create(
            combat_session=session,
            encounter_enemy=encounter_enemy,
            defaults={
                'participant_type': 'enemy',
                'initiative': 10,
                'current_hp': 15,
                'max_hp': 15,
                'armor_class': 13
            }
        )
        session.participants.add(enemy_participant)
        
        self.stdout.write(f'  Added participants: {char_participant.get_name()}, {enemy_participant.get_name()}')
        
        # Start combat
        session.status = 'active'
        session.current_round = 1
        session.current_turn_index = 0
        session.started_at = timezone.now() - timedelta(minutes=30)
        session.save()
        
        self.stdout.write('  Combat started')
        
        # Simulate combat actions
        self.stdout.write('\n  Simulating combat actions...')
        
        # Round 1, Turn 1: Character attacks
        roll, _ = roll_d20()
        attack_total = roll + 4 + 3  # STR mod + proficiency
        hit = attack_total >= enemy_participant.armor_class
        damage = 0
        if hit:
            damage, _ = calculate_damage('1d8+4', 4, roll == 20)
            enemy_participant.current_hp = max(0, enemy_participant.current_hp - damage)
        
        CombatAction.objects.create(
            combat_session=session,
            actor=char_participant,
            target=enemy_participant,
            action_type='attack',
            attack_name='Longsword',
            attack_roll=roll,
            attack_total=attack_total,
            hit=hit,
            damage_amount=damage if hit else None,
            critical=(roll == 20),
            damage_type=slashing,
            round_number=1,
            turn_number=1,
            description=f'Attack roll: {roll}, Total: {attack_total}, {"Hit" if hit else "Miss"}'
        )
        self.stdout.write(f'    Round 1, Turn 1: {char_participant.get_name()} attacks {enemy_participant.get_name()} - {"Hit" if hit else "Miss"} ({damage} damage)')
        
        # Round 1, Turn 2: Enemy attacks
        roll, _ = roll_d20()
        attack_total = roll + 3 + 2  # STR mod + proficiency
        hit = attack_total >= char_participant.armor_class
        damage = 0
        if hit:
            damage, _ = calculate_damage('1d6+3', 3, roll == 20)
            char_participant.current_hp = max(0, char_participant.current_hp - damage)
        
        CombatAction.objects.create(
            combat_session=session,
            actor=enemy_participant,
            target=char_participant,
            action_type='attack',
            attack_name='Greataxe',
            attack_roll=roll,
            attack_total=attack_total,
            hit=hit,
            damage_amount=damage if hit else None,
            critical=(roll == 20),
            damage_type=slashing,
            round_number=1,
            turn_number=2,
            description=f'Attack roll: {roll}, Total: {attack_total}, {"Hit" if hit else "Miss"}'
        )
        self.stdout.write(f'    Round 1, Turn 2: {enemy_participant.get_name()} attacks {char_participant.get_name()} - {"Hit" if hit else "Miss"} ({damage} damage)')
        
        # Round 2, Turn 1: Character casts spell
        spell_damage, _ = calculate_damage('2d6', 0, False)
        enemy_participant.current_hp = max(0, enemy_participant.current_hp - spell_damage)
        
        CombatAction.objects.create(
            combat_session=session,
            actor=char_participant,
            target=enemy_participant,
            action_type='spell',
            attack_name='Magic Missile',
            damage_amount=spell_damage,
            round_number=2,
            turn_number=1,
            description=f'{char_participant.get_name()} casts Magic Missile'
        )
        self.stdout.write(f'    Round 2, Turn 1: {char_participant.get_name()} casts Magic Missile ({spell_damage} damage)')
        
        # Round 2, Turn 2: Enemy dies
        if enemy_participant.current_hp <= 0:
            enemy_participant.is_active = False
            enemy_participant.save()
        
        session.current_round = 2
        session.current_turn_index = 1
        
        # End combat
        session.status = 'ended'
        session.ended_at = timezone.now()
        session.save()
        
        self.stdout.write('  Combat ended')
        
        # Generate log
        log = session.generate_log()
        
        self.stdout.write('\n' + '='*60)
        self.stdout.write('COMBAT LOG GENERATED')
        self.stdout.write('='*60)
        self.stdout.write(f'\nSession ID: {session.id}')
        self.stdout.write(f'Log ID: {log.id}')
        self.stdout.write(f'Rounds: {log.total_rounds}')
        self.stdout.write(f'Turns: {log.total_turns}')
        self.stdout.write(f'Duration: {log.duration_seconds} seconds')
        self.stdout.write(f'Total Damage Dealt: {log.total_damage_dealt}')
        self.stdout.write(f'Total Damage Received: {log.total_damage_received}')
        self.stdout.write(f'\nActions by Type:')
        for action_type, count in log.actions_by_type.items():
            self.stdout.write(f'  {action_type}: {count}')
        self.stdout.write(f'\nParticipant Stats:')
        for pid, stats in log.participant_stats.items():
            self.stdout.write(f'  {stats["name"]}:')
            self.stdout.write(f'    Damage Dealt: {stats["damage_dealt"]}')
            self.stdout.write(f'    Damage Received: {stats["damage_received"]}')
            self.stdout.write(f'    Attacks Made: {stats["attacks_made"]}')
            self.stdout.write(f'    Attacks Hit: {stats["attacks_hit"]}')
            self.stdout.write(f'    Status: {stats["status"]}')
        
        self.stdout.write('\n' + '='*60)
        self.stdout.write('TEST THE LOGGING ENDPOINTS:')
        self.stdout.write('='*60)
        self.stdout.write(f'\n1. Get Statistics:')
        self.stdout.write(f'   GET http://127.0.0.1:8000/api/combat/sessions/{session.id}/stats/')
        self.stdout.write(f'\n2. Get Full Report:')
        self.stdout.write(f'   GET http://127.0.0.1:8000/api/combat/sessions/{session.id}/report/')
        self.stdout.write(f'\n3. Export as JSON:')
        self.stdout.write(f'   GET http://127.0.0.1:8000/api/combat/sessions/{session.id}/export/?format=json')
        self.stdout.write(f'\n4. Export as CSV:')
        self.stdout.write(f'   GET http://127.0.0.1:8000/api/combat/sessions/{session.id}/export/?format=csv')
        self.stdout.write(f'\n5. Get Log Analytics:')
        self.stdout.write(f'   GET http://127.0.0.1:8000/api/combat/logs/{log.id}/analytics/')
        self.stdout.write(f'\n6. Get Character Stats:')
        self.stdout.write(f'   GET http://127.0.0.1:8000/api/characters/{character.id}/combat_stats/')
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('\nTest combat data created successfully!'))
        self.stdout.write(f'\nYou can now test the logging endpoints using the URLs above.')

