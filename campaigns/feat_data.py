
# Configuration for Feats with choices

SKILL_OPTIONS = [
    'Acrobatics', 'Animal Handling', 'Arcana', 'Athletics', 'Deception', 'History',
    'Insight', 'Intimidation', 'Investigation', 'Medicine', 'Nature', 'Perception',
    'Performance', 'Persuasion', 'Religion', 'Sleight of Hand', 'Stealth', 'Survival'
]

TOOL_OPTIONS = [
    'Alchemist\'s supplies', 'Brewer\'s supplies', 'Calligrapher\'s supplies',
    'Carpenter\'s tools', 'Cartographer\'s tools', 'Cobbler\'s tools', 'Cook\'s utensils',
    'Glassblower\'s tools', 'Jeweler\'s tools', 'Leatherworker\'s tools',
    'Mason\'s tools', 'Painter\'s supplies', 'Potter\'s tools', 'Smith\'s tools',
    'Tinker\'s tools', 'Weaver\'s tools', 'Woodcarver\'s tools',
    'Thieves\' tools', 'Herbalism kit', 'Navigator\'s tools', 'Poisoner\'s kit',
    'Disguise kit', 'Forgery kit', 'Gaming set', 'Musical instrument'
]

FEAT_DATA = {
    'Skilled': {
        'choice_limit': 3,
        'options': SKILL_OPTIONS + TOOL_OPTIONS,
        'repeatable': True
    },
    'Magic Initiate (Wizard)': {
         # Placeholder for future logic
         'choice_limit': 0, # Complex handling needed for spells
         'options': [],
         'repeatable': True
    },
    'Elemental Adept': {
        'repeatable': True
    }
}

def get_feat_config(feat_name):
    """
    Get configuration for a feat by name (case-insensitive)
    """
    for name, config in FEAT_DATA.items():
        if name.lower() == feat_name.lower():
            return config
    return {}
