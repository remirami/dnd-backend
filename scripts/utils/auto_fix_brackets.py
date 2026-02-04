#!/usr/bin/env python
"""Automatically fix bracket issues in class_features_data.py"""

import re

def auto_fix_brackets():
    with open('campaigns/class_features_data.py', 'r', encoding='utf-8') as f:
        content = f.read()

    lines = content.split('\n')
    fixed_lines = []
    i = 0

    while i < len(lines):
        line = lines[i]
        fixed_lines.append(line)

        # If this line starts a subclass entry
        if re.match(r"^\s+'[^']+': \{$", line):
            # Find the next subclass entry or the end of the file
            j = i + 1
            bracket_count = 1  # We have the opening {

            while j < len(lines):
                next_line = lines[j]

                # Count brackets in this line
                for char in next_line:
                    if char == '{':
                        bracket_count += 1
                    elif char == '}':
                        bracket_count -= 1

                # If we find the next subclass entry, we need to close the current one
                if re.match(r"^\s+'[^']+': \{$", next_line) and bracket_count > 0:
                    # Add missing closing brackets
                    while bracket_count > 0:
                        if bracket_count % 2 == 1:  # Odd, so we need }
                            fixed_lines.append('    },')
                        else:  # Even, so we need ]
                            fixed_lines.append('        ],')
                        bracket_count -= 1
                    break

                # If we reach a line that would indicate the end of subclasses
                if next_line.strip().startswith('def ') or j == len(lines) - 1:
                    # Add missing closing brackets
                    while bracket_count > 0:
                        if bracket_count % 2 == 1:
                            fixed_lines.append('    },')
                        else:
                            fixed_lines.append('        ],')
                        bracket_count -= 1
                    break

                j += 1

        i += 1

    # Write back
    with open('campaigns/class_features_data.py', 'w', encoding='utf-8') as f:
        f.write('\n'.join(fixed_lines))

if __name__ == "__main__":
    auto_fix_brackets()
    print("Auto-fixed brackets.")
