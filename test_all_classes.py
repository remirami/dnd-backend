#!/usr/bin/env python
"""Test all 12 classes have features"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dnd_backend.settings')
django.setup()

from campaigns.class_features_data import CLASS_FEATURES, get_class_features

print("\n" + "="*70)
print("  CLASS FEATURES COVERAGE TEST")
print("="*70 + "\n")

all_classes = [
    'barbarian', 'bard', 'cleric', 'druid', 'fighter', 'monk',
    'paladin', 'ranger', 'rogue', 'sorcerer', 'warlock', 'wizard'
]

print(f"Testing {len(all_classes)} classes...\n")

for class_name in all_classes:
    if class_name in CLASS_FEATURES:
        # Count features
        total_features = 0
        levels_with_features = 0
        
        for level in range(1, 21):
            features = get_class_features(class_name, level)
            if features:
                total_features += len(features)
                levels_with_features += 1
        
        status = "[PASS]" if total_features > 0 else "[FAIL]"
        print(f"{status} {class_name.capitalize():12} - {total_features:3} features across {levels_with_features:2} levels")
        
        # Show sample features at level 1 and 5
        level_1 = get_class_features(class_name, 1)
        if level_1:
            print(f"       Level 1: {', '.join([f['name'] for f in level_1])}")
        
        level_5 = get_class_features(class_name, 5)
        if level_5:
            print(f"       Level 5: {', '.join([f['name'] for f in level_5])}")
        print()
    else:
        print(f"[FAIL] {class_name.capitalize():12} - NOT FOUND IN DATA")
        print()

print("="*70)
print(f"  Total Classes: {len(all_classes)}")
print(f"  Implemented: {len([c for c in all_classes if c in CLASS_FEATURES])}")
print("="*70 + "\n")



