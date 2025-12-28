"""
Merge Open5e subclasses with existing subclass_features_data.py

This script reads the imported Open5e data and merges it with our existing
manually-created subclasses, avoiding duplicates.
"""

import re

def read_open5e_data():
    """Read the Open5e import file"""
    with open('open5e_subclasses_import.txt', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Remove comments
    lines = [line for line in content.split('\n') if not line.strip().startswith('#')]
    return '\n'.join(lines)

def read_existing_subclasses():
    """Read existing subclasses from class_features_data.py"""
    with open('class_features_data.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find SUBCLASS_FEATURES section
    match = re.search(r'SUBCLASS_FEATURES\s*=\s*\{(.*?)\n\}', content, re.DOTALL)
    if match:
        return match.group(1)
    return ""

def extract_subclass_names(content):
    """Extract subclass names from Python dict content"""
    pattern = r"'([^']+)':\s*\{"
    matches = re.findall(pattern, content)
    return set(matches)

def merge_and_save():
    """Merge Open5e data with existing data"""
    print("Reading existing subclasses...")
    existing_content = read_existing_subclasses()
    existing_names = extract_subclass_names(existing_content)
    
    print(f"Found {len(existing_names)} existing subclasses:")
    for name in sorted(existing_names):
        print(f"  - {name}")
    
    print("\nReading Open5e subclasses...")
    open5e_content = read_open5e_data()
    open5e_names = extract_subclass_names(open5e_content)
    
    print(f"Found {len(open5e_names)} Open5e subclasses")
    
    # Find new subclasses
    new_subclasses = open5e_names - existing_names
    duplicate_subclasses = open5e_names & existing_names
    
    print(f"\n{len(new_subclasses)} new subclasses to add:")
    for name in sorted(new_subclasses):
        print(f"  + {name}")
    
    if duplicate_subclasses:
        print(f"\n{len(duplicate_subclasses)} duplicate subclasses (will keep existing):")
        for name in sorted(duplicate_subclasses):
            print(f"  = {name}")
    
    # Create merged content
    print("\nCreating merged file...")
    
    # Read full class_features_data.py
    with open('class_features_data.py', 'r', encoding='utf-8') as f:
        full_content = f.read()
    
    # Find where to insert new subclasses (before the closing brace of SUBCLASS_FEATURES)
    # We'll insert after the last existing subclass
    
    # Extract only new subclasses from open5e_content
    new_subclass_lines = []
    in_subclass = False
    current_subclass = None
    subclass_content = []
    
    for line in open5e_content.split('\n'):
        # Check if this is a new subclass definition
        match = re.match(r"\s*'([^']+)':\s*\{", line)
        if match:
            # Save previous subclass if it was new
            if current_subclass and current_subclass in new_subclasses:
                new_subclass_lines.extend(subclass_content)
            
            # Start new subclass
            current_subclass = match.group(1)
            subclass_content = [line]
            in_subclass = True
        elif in_subclass:
            subclass_content.append(line)
            # Check if subclass definition ended
            if line.strip() == '},':
                if current_subclass in new_subclasses:
                    new_subclass_lines.extend(subclass_content)
                    new_subclass_lines.append('')  # Add blank line
                in_subclass = False
                subclass_content = []
    
    # Insert new subclasses before the closing of SUBCLASS_FEATURES
    pattern = r'(SUBCLASS_FEATURES\s*=\s*\{.*?)(^\})'
    
    new_content_str = '\n'.join(new_subclass_lines)
    
    def replacer(match):
        return match.group(1) + '\n' + new_content_str + '\n' + match.group(2)
    
    merged_content = re.sub(pattern, replacer, full_content, flags=re.MULTILINE | re.DOTALL)
    
    # Save merged file
    with open('class_features_data.py', 'w', encoding='utf-8') as f:
        f.write(merged_content)
    
    print(f"\n[SUCCESS] Merged! Added {len(new_subclasses)} new subclasses to class_features_data.py")
    print(f"[SUCCESS] Total subclasses now: {len(existing_names) + len(new_subclasses)}")

if __name__ == '__main__':
    merge_and_save()

