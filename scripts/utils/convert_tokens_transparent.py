"""
Utility script to convert solid light/white backgrounds in HeroForge token screenshots
into clean transparent PNGs with alpha channels.

Usage:
    python scripts/utils/convert_tokens_transparent.py
"""

import os
from pathlib import Path

def convert_image_transparent(image_path: Path, output_path: Path = None, threshold: int = 240):
    try:
        from PIL import Image
    except ImportError:
        print("Pillow not installed. Run: pip install Pillow")
        return False

    if output_path is None:
        output_path = image_path

    img = Image.open(image_path).convert("RGBA")
    datas = img.getdata()

    new_data = []
    for item in datas:
        # If pixel is near-white or light neutral grey
        r, g, b, a = item
        if r >= threshold and g >= threshold and b >= threshold:
            # Fully transparent
            new_data.append((255, 255, 255, 0))
        elif r >= threshold - 20 and g >= threshold - 20 and b >= threshold - 20 and abs(r - g) < 10 and abs(g - b) < 10:
            # Soft feathered edge
            fade = int(255 * (1 - (min(r, g, b) - (threshold - 20)) / 20))
            new_data.append((r, g, b, max(0, min(255, fade))))
        else:
            new_data.append(item)

    img.putdata(new_data)
    img.save(output_path, "PNG")
    print(f"Processed: {image_path.name}")
    return True

def process_all_tokens():
    base_dir = Path(__file__).resolve().parent.parent.parent.parent / "dnd-frontend" / "public" / "tokens"
    if not base_dir.exists():
        print(f"Directory not found: {base_dir}")
        return

    count = 0
    for root, _, files in os.walk(base_dir):
        for f in files:
            if f.lower().endswith(('.png', '.jpg', '.jpeg')):
                p = Path(root) / f
                if p.name.lower() != "readme.md":
                    if convert_image_transparent(p):
                        count += 1

    print(f"Finished processing {count} token images.")

if __name__ == "__main__":
    process_all_tokens()
