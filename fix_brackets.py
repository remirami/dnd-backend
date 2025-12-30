#!/usr/bin/env python
"""Script to fix bracket issues in class_features_data.py"""

import re

def fix_brackets_in_file():
    with open('campaigns/class_features_data.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # Pattern to find subclass entries that are missing closing brackets
    # Look for patterns like:
    # 'Subclass Name': {
    #     level: [
    #         {
    #             'name': '...',
    #             'description': '...'
    #         },
    #     <-- Missing ], and }, here

    lines = content.split('\n')
    fixed_lines = []
    i = 0

    while i < len(lines):
        line = lines[i]
        fixed_lines.append(line)

        # If this line starts a subclass entry
        if re.match(r"^\s+'[^']+': \{$", line):
            subclass_start = i
            # Find the feature dictionary that follows
            j = i + 1
            while j < len(lines):
                if re.match(r"^\s+\},\s*$", lines[j]):  # End of feature dict
                    # Check if we have the closing brackets
                    k = j + 1
                    has_list_close = False
                    has_dict_close = False

                    # Skip empty lines
                    while k < len(lines) and lines[k].strip() == '':
                        k += 1

                    # Check for ], and },
                    if k < len(lines) and re.match(r"^\s+\],\s*$", lines[k]):
                        has_list_close = True
                        k += 1
                        # Skip empty lines
                        while k < len(lines) and lines[k].strip() == '':
                            k += 1
                        if k < len(lines) and re.match(r"^\s+\},\s*$", lines[k]):
                            has_dict_close = True

                    # If missing brackets, add them
                    if not has_list_close:
                        fixed_lines.append("        ],")
                    if not has_dict_close:
                        fixed_lines.append("    },")
                    break
                j += 1

        i += 1

    # Write back the fixed content
    with open('campaigns/class_features_data.py', 'w', encoding='utf-8') as f:
        f.write('\n'.join(fixed_lines))

if __name__ == "__main__":
    fix_brackets_in_file()
    print("Bracket fixes applied.")
