#!/usr/bin/env python
"""
D&D 5e Combat Simulator Backend Setup Script
"""

import os
import sys
import subprocess

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e.stderr}")
        return False

def main():
    """Main setup function"""
    print("🎲 Setting up D&D 5e Combat Simulator Backend...")
    
    # Check if we're in the right directory
    if not os.path.exists('manage.py'):
        print("❌ Please run this script from the project root directory")
        sys.exit(1)
    
    # Install requirements
    if not run_command("pip install -r requirements.txt", "Installing dependencies"):
        print("❌ Failed to install dependencies. Please check your Python environment.")
        sys.exit(1)
    
    # Run migrations
    if not run_command("python manage.py migrate", "Running database migrations"):
        print("❌ Failed to run migrations. Please check your database configuration.")
        sys.exit(1)
    
    # Populate base data
    if not run_command("python manage.py populate_dnd_data", "Populating D&D data"):
        print("⚠️  Warning: Failed to populate D&D data. You can run this manually later.")
    
    if not run_command("python manage.py populate_conditions_environments", "Populating conditions and environments"):
        print("⚠️  Warning: Failed to populate conditions and environments. You can run this manually later.")
    
    # Create superuser (optional)
    print("\n🔐 Would you like to create a superuser for the admin interface? (y/n)")
    create_superuser = input().lower().strip()
    if create_superuser in ['y', 'yes']:
        run_command("python manage.py createsuperuser", "Creating superuser")
    
    print("\n🎉 Setup completed successfully!")
    print("\n📋 Next steps:")
    print("1. Start the development server: python manage.py runserver")
    print("2. Visit the API: http://127.0.0.1:8000/api/")
    print("3. Visit the admin: http://127.0.0.1:8000/admin/")
    print("4. Visit the import interface: http://127.0.0.1:8000/api/enemies/import/")
    print("\n🎲 Happy gaming!")

if __name__ == "__main__":
    main()
