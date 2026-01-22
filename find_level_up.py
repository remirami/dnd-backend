
import os

path = r"c:\dnd-backend\dnd-backend\characters\views.py"
with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()
    for i, line in enumerate(lines):
        if "def eligible_subclasses" in line:
            print(f"Found on line {i+1}: {line.strip()}")
