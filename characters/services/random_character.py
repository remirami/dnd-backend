"""
Service for generating randomized Level 1 characters.
"""
import random
from typing import Dict, Any, Optional
from django.contrib.auth.models import User
from characters.models import (
    Character, CharacterClass, CharacterRace, CharacterBackground,
    CharacterStats, CharacterItem, CharacterSpell
)
from characters.serializers import CharacterSerializer
from characters.starting_equipment import get_starting_equipment_for_class, get_equipment_pack
from characters.starting_spells import get_spell_selection_requirements
from characters.inventory_management import equip_item, recalculate_armor_class
from spells.models import Spell
from items.models import Item, ItemCategory


# Class ability stat priorities (descending: primary -> secondary -> tertiary -> dump)
CLASS_STAT_PRIORITIES = {
    'barbarian': ['strength', 'constitution', 'dexterity', 'wisdom', 'charisma', 'intelligence'],
    'bard': ['charisma', 'dexterity', 'constitution', 'wisdom', 'intelligence', 'strength'],
    'cleric': ['wisdom', 'constitution', 'strength', 'dexterity', 'charisma', 'intelligence'],
    'druid': ['wisdom', 'constitution', 'dexterity', 'intelligence', 'charisma', 'strength'],
    'fighter': ['strength', 'constitution', 'dexterity', 'wisdom', 'intelligence', 'charisma'],
    'monk': ['dexterity', 'wisdom', 'constitution', 'strength', 'charisma', 'intelligence'],
    'paladin': ['strength', 'charisma', 'constitution', 'wisdom', 'dexterity', 'intelligence'],
    'ranger': ['dexterity', 'wisdom', 'constitution', 'strength', 'intelligence', 'charisma'],
    'rogue': ['dexterity', 'constitution', 'intelligence', 'wisdom', 'charisma', 'strength'],
    'sorcerer': ['charisma', 'constitution', 'dexterity', 'wisdom', 'intelligence', 'strength'],
    'warlock': ['charisma', 'constitution', 'dexterity', 'wisdom', 'intelligence', 'strength'],
    'wizard': ['intelligence', 'constitution', 'dexterity', 'wisdom', 'charisma', 'strength'],
}

FANTASY_NAMES_BY_RACE = {
    'dwarf': {
        'first': ['Thorin', 'Balin', 'Dwalin', 'Gimli', 'Thora', 'Helga', 'Krag', 'Rurik', 'Brak', 'Orsik', 'Vondal', 'Hlin', 'Kathra', 'Eldeth'],
        'last': ['Ironfoot', 'Battlehammer', 'Stonekeeper', 'Coppervein', 'Frostbeard', 'Deepdelver', 'Fireforge', 'Goldseeker']
    },
    'elf': {
        'first': ['Aerin', 'Legolas', 'Thranduil', 'Tauriel', 'Galadriel', 'Elrond', 'Sylph', 'Faelar', 'Sylas', 'Theron', 'Lia', 'Caelynn', 'Sariel'],
        'last': ['Moonwhisper', 'Starbreeze', 'Silverfrond', 'Nightbreeze', 'Windrunner', 'Autumnfall', 'Sunstrider', 'Dawnseeker']
    },
    'human': {
        'first': ['Roderick', 'William', 'Kaelen', 'Lyra', 'Elena', 'Rowan', 'Cedric', 'Gareth', 'Althea', 'Aric', 'Cora', 'Devon', 'Evelyn'],
        'last': ['Stormwind', 'Blackwood', 'Hawthorne', 'Rivers', 'Crownguard', 'Stoneworth', 'Vale', 'Ironwood', 'Oakheart']
    },
    'halfling': {
        'first': ['Meriadoc', 'Peregrin', 'Milo', 'Rosie', 'Cora', 'Perrin', 'Finn', 'Pip', 'Callie', 'Bree', 'Alton', 'Kithri'],
        'last': ['Swiftfoot', 'Goodbarrel', 'Tealeaf', 'Underbough', 'Brushgather', 'Greenbottle', 'High-hill', 'Tosscobble']
    },
    'dragonborn': {
        'first': ['Rhogar', 'Balasar', 'Torinn', 'Mehen', 'Sora', 'Kava', 'Mishann', 'Nala', 'Arjhan', 'Donaar', 'Harann', 'Heskan'],
        'last': ['Daardendrian', 'Clethtinthiallor', 'Norixius', 'Verthisathurgiesh', 'Myastan', 'Nemmonis', 'Linxakasendalor']
    },
    'gnome': {
        'first': ['Boddynock', 'Dimble', 'Fonkin', 'Gimble', 'Breena', 'Caramip', 'Donella', 'Zook', 'Warryn', 'Ella', 'Gerbo'],
        'last': ['Beren', 'Daergel', 'Folkor', 'Garrick', 'Nackle', 'Murnig', 'Ningel', 'Scheppen', 'Timbers']
    },
    'half-elf': {
        'first': ['Kaelen', 'Tanis', 'Lyra', 'Theron', 'Elena', 'Faelar', 'Sylas', 'Rowan', 'Aric', 'Sariel'],
        'last': ['Silverstring', 'Half-Oak', 'Wanderer', 'Moonriver', 'Fairstep', 'Winterborn']
    },
    'half-orc': {
        'first': ['Grakk', 'Thokk', 'Dench', 'Feng', 'Holg', 'Krag', 'Baggi', 'Emen', 'Myev', 'Shautha', 'Ovak', 'Imsh'],
        'last': ['Ironhide', 'Skullcrusher', 'Bloodfist', 'Thunderbrow', 'Bonebreaker', 'Stonetooth']
    },
    'tiefling': {
        'first': ['Malakir', 'Zephyr', 'Kallista', 'Akmenos', 'Damakos', 'Ekemon', 'Leucis', 'Criella', 'Anakis', 'Nemeia', 'Orianna'],
        'last': ['Dusk', 'Ashen', 'Shadow', 'Creed', 'Sorrow', 'Valor', 'Torment', 'Whisper']
    },
}

IDEALS_LIST = [
    "Freedom. Chains are made to be broken, as are those who would forge them.",
    "Honor. If I give my word, I will keep it until my final breath.",
    "Knowledge. The path to power and self-improvement is paved with wisdom.",
    "Community. We have a sacred duty to protect those who cannot protect themselves.",
    "Respect. All folk deserve to be treated with dignity and fairness.",
    "Glory. My deeds will echo in song and legend long after I am gone.",
    "Discovery. The world is vast and full of forgotten wonders waiting to be uncovered."
]

BONDS_LIST = [
    "I will do whatever it takes to protect the companions who stand beside me.",
    "I seek to prove myself worthy of my ancestors' noble legacy.",
    "An ancient heirloom or unanswered debt drives me out into the wider world.",
    "My loyalty to my allies is unwavering, no matter the danger.",
    "I swore an oath to avenge my fallen mentor and restore their honor."
]

FLAWS_LIST = [
    "I have a hard time resisting a boastful wager or a physical challenge.",
    "I am overly suspicious of anyone who claims to act out of pure altruism.",
    "I speak my mind bluntly before thinking about the consequences.",
    "I tend to dive straight into danger headfirst, planning as I go.",
    "I find it difficult to back down once my pride has been bruised."
]

MARTIAL_WEAPONS = ['Longsword', 'Greatsword', 'Battleaxe', 'Rapier', 'Shortsword', 'Halberd', 'Warhammer', 'Maul', 'Glaive']
SIMPLE_WEAPONS = ['Dagger', 'Mace', 'Spear', 'Quarterstaff', 'Handaxe', 'Light Crossbow', 'Shortbow']

# SRD5e official starting pouch gold by background
BACKGROUND_STARTING_GOLD = {
    'acolyte': 15,
    'charlatan': 15,
    'criminal': 15,
    'entertainer': 15,
    'folk-hero': 10,
    'guild-artisan': 15,
    'hermit': 5,
    'noble': 25,
    'outlander': 10,
    'sage': 10,
    'sailor': 10,
    'soldier': 10,
    'urchin': 10,
}


def calculate_starting_gold(background: Optional[CharacterBackground] = None) -> int:
    """
    Calculate starting gold based on D&D 5e background pouch wealth.
    Since random characters already receive complete starting equipment
    (weapons, armor, class packs), starting gold represents their background purse.
    Includes a slight pocket change variation (+0 to 5 gp).
    """
    if background and background.name:
        bg_slug = background.name.lower().replace(' ', '-')
        base = BACKGROUND_STARTING_GOLD.get(bg_slug)
        if base is not None:
            return base + random.randint(0, 5)
    return random.randint(10, 20)



def roll_4d6_drop_lowest() -> int:
    """Roll 4d6 and drop the lowest die."""
    rolls = [random.randint(1, 6) for _ in range(4)]
    rolls.sort()
    return sum(rolls[1:])


def generate_random_name(race_name: str) -> str:
    """Generate a thematic fantasy name based on race."""
    clean_race = race_name.split('(')[0].strip().lower()
    
    # Try exact match or partial match in FANTASY_NAMES_BY_RACE
    name_data = FANTASY_NAMES_BY_RACE.get(clean_race)
    if not name_data:
        for key in FANTASY_NAMES_BY_RACE:
            if key in clean_race:
                name_data = FANTASY_NAMES_BY_RACE[key]
                break

    if not name_data:
        name_data = FANTASY_NAMES_BY_RACE['human']

    first = random.choice(name_data['first'])
    last = random.choice(name_data['last'])
    return f"{first} {last}"


def select_random_subclass(class_name: str, ruleset_version: str = '2014') -> Optional[str]:
    """Pick level 1 subclass if class gets one at level 1 (e.g. 2014 Cleric, Sorcerer, Warlock)."""
    clean_class = class_name.split('(')[0].strip().lower()
    if ruleset_version == '2014':
        if clean_class == 'cleric':
            return random.choice(['Life Domain', 'Light Domain', 'War Domain', 'Tempest Domain', 'Trickery Domain', 'Knowledge Domain'])
        elif clean_class == 'sorcerer':
            return random.choice(['Draconic Bloodline', 'Wild Magic'])
        elif clean_class == 'warlock':
            return random.choice(['The Fiend', 'The Archfey', 'The Great Old One'])
    return None


def generate_random_character_data(
    ruleset_version: str = '2014',
    character_class_id: Optional[int] = None,
    race_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Generate the complete configuration data for a random level 1 character.
    Used for previewing in the wizard or direct creation.
    """
    # 1. Pick Race
    if race_id:
        race = CharacterRace.objects.get(pk=race_id)
    else:
        race_qs = CharacterRace.objects.filter(source_ruleset__in=[ruleset_version, 'all'])
        if not race_qs.exists():
            race_qs = CharacterRace.objects.all()
        race = random.choice(list(race_qs))

    # 2. Pick Class
    if character_class_id:
        character_class = CharacterClass.objects.get(pk=character_class_id)
    else:
        class_qs = CharacterClass.objects.filter(source_ruleset__in=[ruleset_version, 'all'])
        if not class_qs.exists():
            class_qs = CharacterClass.objects.all()
        character_class = random.choice(list(class_qs))

    clean_class_name = character_class.name.split('(')[0].strip().lower()

    # 3. Pick Background
    bg_qs = CharacterBackground.objects.filter(source_ruleset__in=[ruleset_version, 'all'])
    if not bg_qs.exists():
        bg_qs = CharacterBackground.objects.all()
    background = random.choice(list(bg_qs)) if bg_qs.exists() else None

    # 4. Roll ability scores (4d6 drop lowest) & assign to class priorities
    rolled_scores = sorted([roll_4d6_drop_lowest() for _ in range(6)], reverse=True)
    priority = CLASS_STAT_PRIORITIES.get(clean_class_name, ['strength', 'constitution', 'dexterity', 'wisdom', 'intelligence', 'charisma'])

    # Optional 25% chance of dexterity-based fighter
    if clean_class_name == 'fighter' and random.random() < 0.25:
        priority = ['dexterity', 'constitution', 'strength', 'wisdom', 'intelligence', 'charisma']

    ability_scores = {}
    for stat_name, score in zip(priority, rolled_scores):
        ability_scores[stat_name] = score

    # 5. Alignment, name, personality
    alignments = ['NG', 'CG', 'LG', 'N', 'CN', 'LN']
    alignment = random.choice(alignments)
    name = generate_random_name(race.name)
    subclass = select_random_subclass(character_class.name, ruleset_version)

    # 6. Equipment selections
    equip_data = get_starting_equipment_for_class(clean_class_name)
    equipment_selections = {}
    if equip_data and 'choices' in equip_data:
        for choice in equip_data['choices']:
            choice_num = choice['choice_number']
            if choice['options']:
                chosen_opt = random.choice(choice['options'])
                equipment_selections[str(choice_num)] = chosen_opt['label']

                # Handle sub choices if option contains placeholders
                choice_idx = 0
                for item_ref in chosen_opt.get('items', []):
                    item_name_lower = item_ref['name'].lower()
                    if 'choice' in item_name_lower:
                        if 'martial' in item_name_lower:
                            sub_pick = random.choice(MARTIAL_WEAPONS)
                        elif 'simple' in item_name_lower:
                            sub_pick = random.choice(SIMPLE_WEAPONS)
                        else:
                            sub_pick = random.choice(MARTIAL_WEAPONS)
                        
                        equipment_selections[f"{choice_num}_sub_{choice_idx}"] = sub_pick
                        equipment_selections[f"{choice_num}_sub"] = sub_pick  # for fallback compatibility
                        choice_idx += 1

    # 7. Starting Spells
    cantrip_ids = []
    spell_ids = []
    requirements = get_spell_selection_requirements(clean_class_name)

    if requirements:
        # Fetch available cantrips
        avail_cantrips = list(Spell.objects.filter(
            level=0,
            classes__name__iexact=clean_class_name
        ).values_list('id', flat=True))

        cantrip_count = requirements.get('cantrips_count', 0)
        if avail_cantrips and cantrip_count > 0:
            cantrip_ids = random.sample(avail_cantrips, min(cantrip_count, len(avail_cantrips)))

        # Leveled spells
        avail_lvl1_spells = list(Spell.objects.filter(
            level=1,
            classes__name__iexact=clean_class_name
        ).values_list('id', flat=True))

        spells_info = requirements.get('spells_info') or {}
        spells_needed = spells_info.get('count', 0)

        # For prepared casters (Cleric/Druid), calculate 1 + mod for starting prepared spells
        if spells_needed == 0 and spells_info.get('can_prepare_all'):
            wis_mod = (ability_scores.get('wisdom', 10) - 10) // 2
            spells_needed = max(1, 1 + wis_mod)

        if avail_lvl1_spells and spells_needed > 0:
            spell_ids = random.sample(avail_lvl1_spells, min(spells_needed, len(avail_lvl1_spells)))

    # Calculate estimated HP and AC
    con_mod = (ability_scores['constitution'] - 10) // 2
    dex_mod = (ability_scores['dexterity'] - 10) // 2
    hit_dice_map = {'d6': 6, 'd8': 8, 'd10': 10, 'd12': 12}
    die_size = hit_dice_map.get(character_class.hit_dice, 8)
    hit_points = max(1, die_size + con_mod)
    armor_class = 10 + dex_mod

    # Rolled starting gold (Background pouch: typically 10-25 gp)
    gold_pieces = calculate_starting_gold(background)

    cantrip_names = list(Spell.objects.filter(id__in=cantrip_ids).values_list('name', flat=True))
    spell_names = list(Spell.objects.filter(id__in=spell_ids).values_list('name', flat=True))

    return {
        'name': name,
        'ruleset_version': ruleset_version,
        'race_id': race.id,
        'race_name': race.name,
        'character_class_id': character_class.id,
        'character_class_name': character_class.name,
        'background_id': background.id if background else None,
        'background_name': background.name if background else None,
        'subclass': subclass,
        'alignment': alignment,
        'bonds': random.choice(BONDS_LIST),
        'flaws': random.choice(FLAWS_LIST),
        'ideals': random.choice(IDEALS_LIST),
        'hp_method': 'fixed',
        'hit_points': hit_points,
        'armor_class': armor_class,
        'gold_pieces': gold_pieces,
        'strength': ability_scores['strength'],
        'dexterity': ability_scores['dexterity'],
        'constitution': ability_scores['constitution'],
        'intelligence': ability_scores['intelligence'],
        'wisdom': ability_scores['wisdom'],
        'charisma': ability_scores['charisma'],
        'equipment_selections': equipment_selections,
        'cantrip_ids': cantrip_ids,
        'cantrip_names': cantrip_names,
        'spell_ids': spell_ids,
        'spell_names': spell_names,
        'language_ids': [],
    }


def create_random_character(
    user: User,
    ruleset_version: str = '2014',
    character_class_id: Optional[int] = None,
    race_id: Optional[int] = None,
    character_data: Optional[Dict[str, Any]] = None
) -> Character:
    """
    Generate and persist a full, playable level 1 character to the database.
    If character_data is provided, uses that data directly (e.g. from preview confirmation).
    Otherwise generates fresh random character data.
    """
    if character_data:
        data = character_data
    else:
        data = generate_random_character_data(
            ruleset_version=ruleset_version,
            character_class_id=character_class_id,
            race_id=race_id
        )

    # 1. Create base character via CharacterSerializer
    serializer_payload = {
        'name': data['name'],
        'ruleset_version': data['ruleset_version'],
        'character_class_id': data['character_class_id'],
        'race_id': data['race_id'],
        'background_id': data['background_id'],
        'alignment': data['alignment'],
        'bonds': data['bonds'],
        'flaws': data['flaws'],
        'ideals': data['ideals'],
        'hp_method': data['hp_method'],
        'strength': data['strength'],
        'dexterity': data['dexterity'],
        'constitution': data['constitution'],
        'intelligence': data['intelligence'],
        'wisdom': data['wisdom'],
        'charisma': data['charisma'],
        'language_ids': data['language_ids'],
    }

    serializer = CharacterSerializer(data=serializer_payload)
    serializer.is_valid(raise_exception=True)
    character = serializer.save(user=user)

    # Apply subclass if set (e.g. 2014 Cleric / Sorcerer / Warlock)
    if data.get('subclass'):
        character.subclass = data['subclass']
        character.save(update_fields=['subclass'])

    # 2. Add starting equipment and roll gold
    clean_class = character.character_class.name.split('(')[0].strip().lower()
    equip_data = get_starting_equipment_for_class(clean_class)

    items_to_add = []
    if equip_data:
        selections = data['equipment_selections']
        for choice in equip_data.get('choices', []):
            c_num = choice['choice_number']
            selected_label = selections.get(str(c_num))
            opt_data = next((opt for opt in choice['options'] if opt['label'] == selected_label), None)
            if not opt_data:
                continue

            # Process option items
            choice_sub_idx = 0
            for item_ref in opt_data.get('items', []):
                item_name = item_ref['name']
                qty = item_ref.get('quantity', 1)
                if 'choice' in item_name.lower():
                    sub_name = selections.get(f"{c_num}_sub_{choice_sub_idx}") or selections.get(f"{c_num}_sub")
                    if sub_name:
                        items_to_add.append({'name': sub_name, 'quantity': qty})
                    choice_sub_idx += 1
                else:
                    items_to_add.append(item_ref)

            # Process pack
            if 'pack' in opt_data:
                pack_name = opt_data['pack']
                pack_data = get_equipment_pack(pack_name)
                if pack_data:
                    items_to_add.extend(pack_data.get('items', []))
                    try:
                        gear_cat, _ = ItemCategory.objects.get_or_create(name="Adventuring Gear")
                        Item.objects.get_or_create(
                            name=pack_name,
                            defaults={
                                'description': f"Equipment pack: {pack_name}",
                                'category': gear_cat,
                                'weight': 0,
                                'value': pack_data.get('cost', 0),
                                'rarity': 'common'
                            }
                        )
                        items_to_add.append({'name': pack_name, 'quantity': 1})
                    except Exception:
                        pass

        # Default items
        items_to_add.extend(equip_data.get('default_items', []))

    # Starting gold (use confirmed preview gold or calculate background purse)
    if data.get('gold_pieces') is not None:
        character.gold_pieces = data['gold_pieces']
    else:
        character.gold_pieces = calculate_starting_gold(character.background)
    character.save(update_fields=['gold_pieces'])

    # Add items to CharacterItem
    for item_spec in items_to_add:
        item_name = item_spec['name']
        quantity = item_spec.get('quantity', 1)
        if 'choice' in item_name.lower():
            continue

        item_obj = Item.objects.filter(name__iexact=item_name).first()
        if item_obj:
            CharacterItem.objects.create(
                character=character,
                item=item_obj,
                quantity=quantity,
                is_equipped=False
            )

    # Auto-equip armor, shield, and a primary weapon
    char_items = CharacterItem.objects.filter(character=character).select_related('item')
    armor_equipped = False
    shield_equipped = False
    weapon_equipped = False

    for ci in char_items:
        it = ci.item
        it_name = it.name.lower()

        # Try equip armor
        if not armor_equipped and (hasattr(it, 'armor') or 'armor' in it_name or 'mail' in it_name or 'leather' in it_name):
            if 'shield' not in it_name:
                success, _, _ = equip_item(character, it, slot='armor')
                if success:
                    armor_equipped = True
                    continue

        # Try equip shield
        if not shield_equipped and ('shield' in it_name):
            success, _, _ = equip_item(character, it, slot='off_hand')
            if success:
                shield_equipped = True
                continue

        # Try equip primary weapon
        if not weapon_equipped and (hasattr(it, 'weapon') or any(w.lower() in it_name for w in MARTIAL_WEAPONS + SIMPLE_WEAPONS)):
            success, _, _ = equip_item(character, it, slot='main_hand')
            if success:
                weapon_equipped = True

    # Recalculate AC after equipment
    recalculate_armor_class(character)

    # 3. Add Starting Spells
    # Cantrips
    for cantrip_id in data.get('cantrip_ids', []):
        spell = Spell.objects.filter(pk=cantrip_id, level=0).first()
        if spell:
            CharacterSpell.objects.create(
                character=character,
                spell=spell,
                name=spell.name,
                level=0,
                school=spell.school,
                is_prepared=True,
                is_ritual=spell.ritual,
                in_spellbook=False,
                description=spell.description
            )

    # Leveled spells
    is_wizard = clean_class == 'wizard'
    wizard_int_mod = (character.stats.intelligence - 10) // 2
    wizard_prep_limit = max(1, 1 + wizard_int_mod)

    for idx, spell_id in enumerate(data.get('spell_ids', [])):
        spell = Spell.objects.filter(pk=spell_id, level=1).first()
        if spell:
            if is_wizard:
                # Wizard: all in spellbook, first N prepared
                CharacterSpell.objects.create(
                    character=character,
                    spell=spell,
                    name=spell.name,
                    level=1,
                    school=spell.school,
                    is_prepared=(idx < wizard_prep_limit),
                    is_ritual=spell.ritual,
                    in_spellbook=True,
                    description=spell.description
                )
            else:
                # Known casters & prepared casters
                CharacterSpell.objects.create(
                    character=character,
                    spell=spell,
                    name=spell.name,
                    level=1,
                    school=spell.school,
                    is_prepared=True,
                    is_ritual=spell.ritual,
                    in_spellbook=False,
                    description=spell.description
                )

    character.refresh_from_db()
    return character
