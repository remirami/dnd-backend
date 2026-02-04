
import os

path = r"c:\dnd-backend\dnd-backend\campaigns\class_features_data.py"
with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()
    for i, line in enumerate(lines):
        if "def get_class_features" in line:
            print(f"Found on line {i+1}")
            # print surrounding lines
            for j in range(max(0, i-5), min(len(lines), i+20)):
                print(f"{j+1}: {lines[j].rstrip()}")
            break
