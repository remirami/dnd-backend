
import os
import django
import sys

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dnd_backend.settings')
django.setup()

try:
    from campaigns.class_features_data import AVAILABLE_SUBCLASSES
    print(f"Fighter Subclasses: {AVAILABLE_SUBCLASSES.get('Fighter', 'NOT FOUND')}")
except ImportError as e:
    print(f"FAILURE: {e}")
except Exception as e:
    print(f"ERROR: {e}")
