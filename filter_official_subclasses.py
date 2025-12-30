#!/usr/bin/env python
"""Filter the Open5e subclasses to only include official D&D 5e core subclasses"""

import re

# Official D&D 5e core subclasses (from "5e Core Rules")
OFFICIAL_SUBCLASSES = {
    'Path of the Berserker',  # Barbarian
    'College of Lore',       # Bard
    'Life Domain',          # Cleric
    'Circle of the Land',   # Druid
    'Champion',             # Fighter
    'Way of the Open Hand', # Monk
    'Oath of Devotion',     # Paladin
    'Hunter',               # Ranger
    'Thief',                # Rogue
    'Draconic Bloodline',   # Sorcerer
    'The Fiend',            # Warlock
    'School of Evocation',  # Wizard
}

def filter_official_subclasses():
    """Filter the generated subclasses file to only include official ones"""

    # Read the generated file
    with open('open5e_subclasses_import.txt', 'r', encoding='utf-8') as f:
        content = f.read()

    # Split into individual subclass blocks
    # Each subclass starts with "    'Subclass Name': {"
    subclass_blocks = re.split(r'(?=\n    \'[^\']+\': \{)', content)

    filtered_blocks = []

    for block in subclass_blocks:
        if not block.strip():
            continue

        # Extract subclass name
        match = re.search(r"'([^']+)': \{", block)
        if match:
            subclass_name = match.group(1)
            if subclass_name in OFFICIAL_SUBCLASSES:
                filtered_blocks.append(block)

    # Combine filtered blocks
    result = "# Official D&D 5e Core Subclasses from Open5e\n"
    result += "# Only includes subclasses from '5e Core Rules'\n\n"
    result += ''.join(filtered_blocks)

    # Write to a new file
    with open('official_subclasses_only.txt', 'w', encoding='utf-8') as f:
        f.write(result)

    print(f"Filtered to {len(OFFICIAL_SUBCLASSES)} official subclasses")
    print("Official subclasses:")
    for name in sorted(OFFICIAL_SUBCLASSES):
        print(f"  - {name}")

if __name__ == "__main__":
    filter_official_subclasses()
