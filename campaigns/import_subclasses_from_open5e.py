"""
Import subclass features from Open5e API

This script fetches all available subclasses from Open5e and adds them
to the class_features_data.py file.
"""

import requests
import re
import json

BASE_URL = "https://api.open5e.com"

def fetch_all_classes():
    """Fetch all classes from Open5e"""
    response = requests.get(f"{BASE_URL}/classes/")
    if response.status_code == 200:
        return response.json()['results']
    return []

def parse_archetype_description(desc, archetype_name):
    """
    Parse archetype description to extract features by level.
    
    Open5e descriptions contain markdown with level headers like:
    ##### Feature Name
    Starting at 3rd level, ...
    """
    features_by_level = {}
    
    # Split by markdown headers (##### )
    sections = re.split(r'#{2,5}\s+', desc)
    
    for section in sections[1:]:  # Skip first empty section
        lines = section.strip().split('\n', 1)
        if not lines:
            continue
            
        feature_name = lines[0].strip()
        feature_desc = lines[1].strip() if len(lines) > 1 else ""
        
        # Try to extract level from description
        level_match = re.search(r'(?:at|when you (?:choose this|reach)|starting at|beginning at|by)\s+(\d+)(?:st|nd|rd|th)\s+level', 
                               feature_desc, re.IGNORECASE)
        
        if level_match:
            level = int(level_match.group(1))
        else:
            # Try to find level in feature name
            level_match = re.search(r'(\d+)(?:st|nd|rd|th)', feature_name)
            if level_match:
                level = int(level_match.group(1))
            else:
                # Default to level 3 if no level found (most subclasses start at 3)
                level = 3
        
        if level not in features_by_level:
            features_by_level[level] = []
        
        features_by_level[level].append({
            'name': feature_name,
            'description': feature_desc[:500] + '...' if len(feature_desc) > 500 else feature_desc
        })
    
    return features_by_level

def generate_subclass_dict():
    """Generate Python dictionary for all subclasses"""
    classes = fetch_all_classes()
    
    all_subclasses = {}
    
    for cls in classes:
        class_name = cls['name']
        archetypes = cls.get('archetypes', [])
        
        print(f"\n{class_name}: Found {len(archetypes)} archetypes")
        
        for archetype in archetypes:
            arch_name = archetype['name']
            arch_desc = archetype['desc']
            source = archetype.get('document__title', 'Unknown')
            
            print(f"  - {arch_name} (from {source})")
            
            # Parse features
            features_by_level = parse_archetype_description(arch_desc, arch_name)
            
            if features_by_level:
                all_subclasses[arch_name] = features_by_level
                print(f"    Levels: {sorted(features_by_level.keys())}")
    
    return all_subclasses

def format_python_dict(subclasses_dict):
    """Format the dictionary as Python code"""
    output = []
    
    for subclass_name in sorted(subclasses_dict.keys()):
        features_by_level = subclasses_dict[subclass_name]
        
        output.append(f"    '{subclass_name}': {{")
        
        for level in sorted(features_by_level.keys()):
            features = features_by_level[level]
            output.append(f"        {level}: [")
            
            for feature in features:
                # Escape quotes in strings
                name = feature['name'].replace("'", "\\'")
                desc = feature['description'].replace("'", "\\'").replace('\n', ' ')
                
                output.append(f"            {{")
                output.append(f"                'name': '{name}',")
                output.append(f"                'description': '{desc}'")
                output.append(f"            }},")
            
            output.append(f"        ],")
        
        output.append(f"    }},")
        output.append("")
    
    return '\n'.join(output)

def main():
    print("="*80)
    print("IMPORTING SUBCLASSES FROM OPEN5E")
    print("="*80)
    
    # Fetch and parse all subclasses
    subclasses_dict = generate_subclass_dict()
    
    print(f"\n{'='*80}")
    print(f"Total subclasses found: {len(subclasses_dict)}")
    print(f"{'='*80}")
    
    # Generate Python code
    python_code = format_python_dict(subclasses_dict)
    
    # Save to file
    output_file = 'open5e_subclasses_import.txt'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# Subclasses imported from Open5e\n")
        f.write("# Add these to SUBCLASS_FEATURES in class_features_data.py\n\n")
        f.write(python_code)
    
    print(f"\nSubclass data saved to: {output_file}")
    print("\nYou can now copy this data into class_features_data.py")
    
    # Print summary
    print(f"\n{'='*80}")
    print("SUMMARY BY CLASS")
    print(f"{'='*80}")
    
    classes = fetch_all_classes()
    for cls in classes:
        archetypes = cls.get('archetypes', [])
        if archetypes:
            print(f"\n{cls['name']}: {len(archetypes)} subclasses")
            for arch in archetypes:
                print(f"  - {arch['name']}")

if __name__ == '__main__':
    main()

