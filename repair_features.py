import os
import django
import sys

# Set up Django environment
sys.path.append('c:\\dnd-backend\\dnd-backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dnd_backend.settings')
django.setup()

from characters.models import CharacterFeature

def repair_student_of_war():
    features = CharacterFeature.objects.filter(name="Student of War")
    print(f"Found {features.count()} 'Student of War' features to repair.")
    
    artisans_tools = [
        'Alchemist\'s supplies', 'Brewer\'s supplies', 'Calligrapher\'s supplies', 
        'Carpenter\'s tools', 'Cartographer\'s tools', 'Cobbler\'s tools', 
        'Cook\'s utensils', 'Glassblower\'s tools', 'Jeweler\'s tools', 
        'Leatherworker\'s tools', 'Mason\'s tools', 'Painter\'s supplies', 
        'Potter\'s tools', 'Smith\'s tools', 'Tinker\'s tools', 
        'Weaver\'s tools', 'Woodcarver\'s tools'
    ]
    
    updated_count = 0
    for feature in features:
        # Check if update is needed
        if not feature.options:
            print(f"Updating feature for character: {feature.character.name}")
            feature.options = artisans_tools
            feature.choice_limit = 1
            feature.save()
            updated_count += 1
        else:
            print(f"Feature for {feature.character.name} already has options.")
            
    print(f"Successfully repaired {updated_count} features.")

if __name__ == "__main__":
    repair_student_of_war()
