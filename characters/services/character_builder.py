"""
Character Builder Service

Main service for guided character creation wizard
"""
from django.db import transaction
from django.utils import timezone
from datetime import timedelta

from characters.builder_models import CharacterBuilderSession
from characters.models import (
    Character, CharacterStats, CharacterClass, CharacterRace,
    CharacterBackground
)
from .validators import (
    AbilityScoreValidator,
    RacialBonusCalculator,
    MulticlassPrerequisiteChecker,
    calculate_modifiers
)


class CharacterBuilderService:
    """Service for managing character creation wizard"""
    
    @staticmethod
    def start_session(user, ability_score_method='standard_array'):
        """
        Start a new character builder session
        
        Args:
            user: User object
            ability_score_method: 'standard_array', 'point_buy', or 'manual'
            
        Returns:
            CharacterBuilderSession
        """
        # Clean up any expired sessions for this user
        CharacterBuilderSession.objects.filter(
            user=user,
            expires_at__lt=timezone.now()
        ).delete()
        
        # Create new session
        session = CharacterBuilderSession.objects.create(
            user=user,
            current_step=1,
            data={
                'method': ability_score_method,
            }
        )
        
        return session
    
    @staticmethod
    def get_session(session_id, user):
        """
        Retrieve a session
        
        Args:
            session_id: UUID of session
            user: User object (for security)
            
        Returns:
            CharacterBuilderSession or None
            
        Raises:
            ValueError: If session expired
        """
        try:
            session = CharacterBuilderSession.objects.get(
                id=session_id,
                user=user
            )
            
            if session.is_expired():
                session.delete()
                raise ValueError("Session has expired")
            
            return session
        except CharacterBuilderSession.DoesNotExist:
            return None
    
    @staticmethod
    def assign_abilities(session, ability_scores):
        """
        Assign ability scores (Step 2)
        
        Args:
            session: CharacterBuilderSession
            ability_scores: dict like {"str": 15, "dex": 14, ...}
            
        Returns:
            (bool, str, dict): (success, error_message, data)
        """
        method = session.data.get('method', 'standard_array')
        
        # Normalize keys to full names
        normalized = {
            'strength': ability_scores.get('str', ability_scores.get('strength', 8)),
            'dexterity': ability_scores.get('dex', ability_scores.get('dexterity', 8)),
            'constitution': ability_scores.get('con', ability_scores.get('constitution', 8)),
            'intelligence': ability_scores.get('int', ability_scores.get('intelligence', 8)),
            'wisdom': ability_scores.get('wis', ability_scores.get('wisdom', 8)),
            'charisma': ability_scores.get('cha', ability_scores.get('charisma', 8)),
        }
        
        # Also support short form in result
        short_form = {
            'str': normalized['strength'],
            'dex': normalized['dexterity'],
            'con': normalized['constitution'],
            'int': normalized['intelligence'],
            'wis': normalized['wisdom'],
            'cha': normalized['charisma'],
        }
        
        # Validate based on method
        if method == 'standard_array':
            valid, error = AbilityScoreValidator.validate_standard_array(short_form)
            if not valid:
                return False, error, {}
        elif method == 'point_buy':
            valid, error, points_used = AbilityScoreValidator.validate_point_buy(short_form)
            if not valid:
                return False, error, {}
        elif method == 'manual':
            valid, error, warnings = AbilityScoreValidator.validate_manual(short_form)
            if not valid:
                return False, error, {}
        else:
            return False, "Invalid ability score method", {}
        
        # Save to session
        session.data['base_scores'] = normalized
        session.current_step = 2
        session.save()
        
        # Calculate modifiers
        modifiers = calculate_modifiers(short_form)
        
        return True, "", {
            'base_scores': normalized,
            'modifiers': modifiers,
            'current_step': 2
        }
    
    @staticmethod
    def choose_race(session, race_id):
        """
        Choose race and apply racial bonuses (Step 3)
        
        Args:
            session: CharacterBuilderSession
            race_id: ID of CharacterRace
            
        Returns:
            (bool, str, dict): (success, error_message, data)
        """
        try:
            race = CharacterRace.objects.get(id=race_id)
        except CharacterRace.DoesNotExist:
            return False, "Race not found", {}
        
        # Get base scores
        base_scores = session.data.get('base_scores')
        if not base_scores:
            return False, "Must assign ability scores first", {}
        
        # Convert to short form for calculator
        short_form = {
            'str': base_scores['strength'],
            'dex': base_scores['dexterity'],
            'con': base_scores['constitution'],
            'int': base_scores['intelligence'],
            'wis': base_scores['wisdom'],
            'cha': base_scores['charisma'],
        }
        
        # Apply racial bonuses
        final_scores_short = RacialBonusCalculator.apply_bonuses(short_form, race)
        
        # Convert back to long form
        final_scores = {
            'strength': final_scores_short['str'],
            'dexterity': final_scores_short['dex'],
            'constitution': final_scores_short['con'],
            'intelligence': final_scores_short['int'],
            'wisdom': final_scores_short['wis'],
            'charisma': final_scores_short['cha'],
        }
        
        # Get bonuses
        bonuses = RacialBonusCalculator.get_bonuses(race)
        
        # Save to session
        session.data['race_id'] = race_id
        session.data['final_scores'] = final_scores
        session.data['racial_bonuses'] = bonuses
        session.current_step = 3
        session.save()
        
        return True, "", {
            'race': {
                'id': race.id,
                'name': race.get_name_display(),
                'size': race.get_size_display(),
                'speed': race.speed
            },
            'racial_bonuses': bonuses,
            'final_scores': final_scores,
            'modifiers': calculate_modifiers(final_scores_short),
            'current_step': 3
        }
    
    @staticmethod
    def choose_class(session, class_id, subclass=None):
        """
        Choose class (Step 4)
        
        Args:
            session: CharacterBuilderSession
            class_id: ID of CharacterClass
            subclass: Optional subclass name
            
        Returns:
            (bool, str, dict): (success, error_message, data)
        """
        try:
            char_class = CharacterClass.objects.get(id=class_id)
        except CharacterClass.DoesNotExist:
            return False, "Class not found", {}
        
        # Check multiclass prerequisites (if this is a later class)
        final_scores = session.data.get('final_scores')
        if not final_scores:
            return False, "Must choose race first", {}
        
        # Short form for checker
        short_scores = {
            'str': final_scores['strength'],
            'dex': final_scores['dexterity'],
            'con': final_scores['constitution'],
            'int': final_scores['intelligence'],
            'wis': final_scores['wisdom'],
            'cha': final_scores['charisma'],
        }
        
        can_multiclass, reason = MulticlassPrerequisiteChecker.can_multiclass_into(
            char_class.name,
            short_scores
        )
        
        if not can_multiclass:
            return False, reason, {}
        
        # Save to session
        session.data['class_id'] = class_id
        if subclass:
            session.data['subclass'] = subclass
        session.current_step = 4
        session.save()
        
        return True, "", {
            'class': {
                'id': char_class.id,
                'name': char_class.get_name_display(),
                'hit_dice': char_class.hit_dice,
                'primary_ability': char_class.primary_ability,
                'saving_throws': char_class.saving_throw_proficiencies.split(',')
            },
            'current_step': 4
        }
    
    @staticmethod
    def choose_background(session, background_id):
        """
        Choose background (Step 5)
        
        Args:
            session: CharacterBuilderSession
            background_id: ID of CharacterBackground
            
        Returns:
            (bool, str, dict): (success, error_message, data)
        """
        try:
            background = CharacterBackground.objects.get(id=background_id)
        except CharacterBackground.DoesNotExist:
            return False, "Background not found", {}
        
        if not session.data.get('class_id'):
            return False, "Must choose class first", {}
        
        # Save to session
        session.data['background_id'] = background_id
        session.current_step = 5
        session.save()
        
        return True, "", {
            'background': {
                'id': background.id,
                'name': background.get_name_display(),
                'skill_proficiencies': background.skill_proficiencies.split(',') if background.skill_proficiencies else [],
                'tool_proficiencies': background.tool_proficiencies.split(',') if background.tool_proficiencies else [],
            },
            'current_step': 5
        }
    
    @staticmethod
    def finalize_character(session, name, alignment='N', hp_method='fixed'):
        """
        Finalize and create the character (Step 7)
        
        Args:
            session: CharacterBuilderSession
            name: Character name
            alignment: Character alignment (default 'N')
            hp_method: HP calculation method ('fixed', 'average', 'manual')
            
        Returns:
            (bool, str, Character): (success, error_message, character)
        """
        # Validate session has all required data
        required_keys = ['final_scores', 'race_id', 'class_id', 'background_id']
        for key in required_keys:
            if key not in session.data:
                return False, f"Missing required data: {key}", None
        
        try:
            with transaction.atomic():
                # Get related objects
                race = CharacterRace.objects.get(id=session.data['race_id'])
                char_class = CharacterClass.objects.get(id=session.data['class_id'])
                background = CharacterBackground.objects.get(id=session.data['background_id'])
                
                # Create character
                character = Character.objects.create(
                    user=session.user,
                    name=name,
                    character_class=char_class,
                    race=race,
                    background=background,
                    level=1,
                    alignment=alignment,
                    subclass=session.data.get('subclass', ''),
                    hp_method=hp_method
                )
                
                # Create stats
                final_scores = session.data['final_scores']
                
                # Calculate HP first (max at level 1)
                hit_dice = char_class.hit_dice  # e.g., "d8", "1d10"
                # Extract die size (handle both "d8" and "1d8" formats)
                die_size = int(hit_dice.split('d')[-1])
                con_mod = (final_scores['constitution'] - 10) // 2
                max_hp = die_size + con_mod
                max_hp = max(1, int(max_hp))  # Minimum 1 HP
                
                dex_mod = (final_scores['dexterity'] - 10) // 2
                
                stats = CharacterStats.objects.create(
                    character=character,
                    strength=final_scores['strength'],
                    dexterity=final_scores['dexterity'],
                    constitution=final_scores['constitution'],
                    intelligence=final_scores['intelligence'],
                    wisdom=final_scores['wisdom'],
                    charisma=final_scores['charisma'],
                    hit_points=max_hp,
                    max_hit_points=max_hp,
                    armor_class=10 + dex_mod  # Base + DEX
                )
                
                # Delete session
                session.delete()
                
                # Apply Racial Skills
                if race.skill_proficiencies:
                    skills = [s.strip() for s in race.skill_proficiencies.split(',')]
                    for skill in skills:
                        # Find proficiency type based on skill name
                        from characters.models import CharacterProficiency
                        CharacterProficiency.objects.create(
                            character=character,
                            skill_name=skill,
                            proficiency_type='skill',
                            proficiency_level='proficient',
                            source='race'
                        )
                
                # Apply Racial Traits
                if race.traits:
                    from characters.models import CharacterFeature
                    for trait in race.traits:
                        CharacterFeature.objects.create(
                            character=character,
                            name=trait.get('name', 'Unknown Trait'),
                            description=trait.get('description', ''),
                            feature_type='racial',
                            source='race',
                        )

                return True, "", character
                
        except Exception as e:
            return False, str(e), None
