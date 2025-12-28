"""
Fix bracket/brace matching issues in class_features_data.py
"""

import re

def fix_subclass_features():
    """Read and fix the SUBCLASS_FEATURES dictionary"""
    
    with open('class_features_data.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Find the SUBCLASS_FEATURES section
    start_idx = None
    end_idx = None
    
    for i, line in enumerate(lines):
        if 'SUBCLASS_FEATURES = {' in line:
            start_idx = i
        if start_idx and line.strip() == '}' and 'def get_subclass_features' in lines[i+2]:
            end_idx = i
            break
    
    if not start_idx or not end_idx:
        print("Could not find SUBCLASS_FEATURES section")
        return
    
    print(f"Found SUBCLASS_FEATURES from line {start_idx} to {end_idx}")
    
    # Extract the section
    section_lines = lines[start_idx:end_idx+1]
    
    # Track bracket depth
    fixed_lines = []
    current_subclass = None
    in_feature_list = False
    in_feature_dict = False
    
    for i, line in enumerate(section_lines):
        stripped = line.strip()
        
        # Check if this is a subclass definition
        if re.match(r"'[^']+': \{", stripped):
            # Close previous subclass if needed
            if current_subclass:
                # Make sure we close the feature list and subclass dict
                if in_feature_dict:
                    fixed_lines.append("            },\n")
                    in_feature_dict = False
                if in_feature_list:
                    fixed_lines.append("        ],\n")
                    in_feature_list = False
                fixed_lines.append("    },\n")
                fixed_lines.append("\n")
            
            current_subclass = stripped
            fixed_lines.append("    " + stripped + "\n")
            continue
        
        # Check if this is a level definition
        if re.match(r'\d+: \[', stripped):
            if in_feature_dict:
                fixed_lines.append("            },\n")
                in_feature_dict = False
            if in_feature_list:
                fixed_lines.append("        ],\n")
            
            fixed_lines.append("        " + stripped + "\n")
            in_feature_list = True
            continue
        
        # Check if this is a feature dict start
        if stripped == '{':
            fixed_lines.append("            {\n")
            in_feature_dict = True
            continue
        
        # Check if this is a feature property
        if "'name':" in stripped or "'description':" in stripped:
            fixed_lines.append("                " + stripped + "\n")
            continue
        
        # Check for closing dict
        if stripped == '},':
            if in_feature_dict:
                fixed_lines.append("            },\n")
                in_feature_dict = False
            continue
        
        # Check for closing list
        if stripped == '],':
            if in_feature_dict:
                fixed_lines.append("            },\n")
                in_feature_dict = False
            fixed_lines.append("        ],\n")
            in_feature_list = False
            continue
        
        # Check for closing subclass dict
        if stripped == '},':
            if in_feature_dict:
                fixed_lines.append("            },\n")
                in_feature_dict = False
            if in_feature_list:
                fixed_lines.append("        ],\n")
                in_feature_list = False
            fixed_lines.append("    },\n")
            current_subclass = None
            continue
        
        # Check for final closing brace
        if stripped == '}' and i == len(section_lines) - 1:
            # Close any open structures
            if in_feature_dict:
                fixed_lines.append("            },\n")
            if in_feature_list:
                fixed_lines.append("        ],\n")
            if current_subclass:
                fixed_lines.append("    },\n")
            fixed_lines.append("}\n")
            continue
        
        # Keep empty lines
        if not stripped:
            fixed_lines.append("\n")
            continue
    
    # Replace the section
    new_lines = lines[:start_idx] + fixed_lines + lines[end_idx+1:]
    
    # Write back
    with open('class_features_data.py', 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    
    print(f"Fixed! Wrote {len(new_lines)} lines")

if __name__ == '__main__':
    fix_brackets()

