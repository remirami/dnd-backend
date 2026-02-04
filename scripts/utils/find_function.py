filename = r"c:\dnd-backend\dnd-backend\campaigns\class_features_data.py"
print(f"Reading {filename}...")
max_lines = 0
with open(filename, 'r', encoding='utf-8') as f:
    for i, line in enumerate(f):
        max_lines = i
        if "def get_class_features" in line:
            print(f"FOUND at line {i+1}: {line.strip()}")
            
print(f"Total lines: {max_lines+1}")
