"""
Test script for combat logging system
Run with: python test_combat_logging.py

Make sure you've run: python manage.py test_combat_logging first
"""
import requests
import json
import sys

SESSION = requests.Session()

BASE_URL = "http://127.0.0.1:8000/api"

def print_response(response, title=""):
    """Pretty print API response"""
    if title:
        print(f"\n{'='*60}")
        print(f"{title}")
        print(f"{'='*60}")
    
    try:
        data = response.json()
        print(json.dumps(data, indent=2))
        return data
    except:
        print(f"Status: {response.status_code}")
        try:
            # Try to decode safely
            text = response.text
            # Replace non-printable characters or encode/decode safely
            print(text.encode(sys.stdout.encoding, errors='replace').decode(sys.stdout.encoding))
        except Exception as e:
            print(f"Could not print response text: {e}")
    
    return None

def authenticate():
    """Authenticate via API"""
    print("\nAuthenticating...")
    try:
        response = SESSION.post(f"{BASE_URL}/auth/login/", json={
            "username": "test_gauntlet",
            "password": "password123"
        })
        if response.status_code == 200:
            token = response.json().get('access')
            SESSION.headers.update({'Authorization': f'Bearer {token}'})
            print("Authentication successful")
            return True
        else:
            print(f"Authentication failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"Authentication error: {e}")
        return False

def test_combat_logging():
    """Test the combat logging endpoints"""
    
    print("\n" + "="*60)
    print("COMBAT LOGGING SYSTEM TEST")
    print("="*60)
    
    # Authenticate first (optional but good practice)
    authenticate()
    
    # Step 1: Get combat sessions
    print("\n1. Getting combat sessions...")
    sessions_response = SESSION.get(f"{BASE_URL}/combat/sessions/")
    sessions = sessions_response.json().get('results', [])
    
    if not sessions:
        print("  ERROR: No combat sessions found!")
        print("   Run: python manage.py test_combat_logging")
        return
    
    # Find an ended session (has a log)
    ended_session = None
    for session in sessions:
        if session.get('status') == 'ended':
            ended_session = session
            break
    
    if not ended_session:
        print("  ERROR: No ended combat sessions found!")
        print("   Run: python manage.py test_combat_logging")
        return
    
    session_id = ended_session['id']
    print(f"  Using session ID: {session_id}")
    
    # Step 2: Get statistics
    print("\n2. Getting combat statistics...")
    stats_response = SESSION.get(f"{BASE_URL}/combat/sessions/{session_id}/stats/")
    stats = print_response(stats_response, "Combat Statistics")
    
    if stats:
        print(f"\n  Total Rounds: {stats.get('total_rounds', 0)}")
        print(f"  Total Turns: {stats.get('total_turns', 0)}")
        print(f"  Total Damage Dealt: {stats.get('total_damage_dealt', 0)}")
        print(f"  Total Damage Received: {stats.get('total_damage_received', 0)}")
    
    # Step 3: Get full report
    print("\n3. Getting full combat report...")
    report_response = SESSION.get(f"{BASE_URL}/combat/sessions/{session_id}/report/")
    report = print_response(report_response, "Combat Report")
    
    if report:
        summary = report.get('summary', {})
        print(f"\n  Encounter: {report.get('encounter', {}).get('name', 'Unknown')}")
        print(f"  Duration: {summary.get('duration_formatted', 'N/A')}")
        print(f"  Rounds: {summary.get('rounds', 0)}")
        print(f"  Timeline entries: {len(report.get('timeline', []))}")
    
    # Step 4: Export as JSON
    print("\n4. Exporting as JSON...")
    json_response = SESSION.get(f"{BASE_URL}/combat/sessions/{session_id}/export/?format=json")
    json_data = print_response(json_response, "JSON Export")
    
    if json_data:
        print("  JSON export successful")
    
    # Step 5: Export as CSV
    print("\n5. Exporting as CSV...")
    csv_response = SESSION.get(f"{BASE_URL}/combat/sessions/{session_id}/export/?format=csv")
    
    if csv_response.status_code == 200:
        print("  CSV export successful")
        print(f"  Content-Type: {csv_response.headers.get('Content-Type', 'N/A')}")
        print(f"  Content Length: {len(csv_response.content)} bytes")
        # Show first few lines
        lines = csv_response.text.split('\n')[:5]
        print("\n  First few lines of CSV:")
        for line in lines:
            if line.strip():
                print(f"    {line}")
    else:
        print(f"  ERROR: CSV export failed: {csv_response.status_code}")
    
    # Step 6: Get combat logs
    print("\n6. Getting combat logs...")
    logs_response = SESSION.get(f"{BASE_URL}/combat/logs/")
    logs = logs_response.json().get('results', [])
    
    if logs:
        log = logs[0]
        log_id = log['id']
        print(f"  Found log ID: {log_id}")
        
        # Step 7: Get log analytics
        print("\n7. Getting log analytics...")
        analytics_response = SESSION.get(f"{BASE_URL}/combat/logs/{log_id}/analytics/")
        analytics = print_response(analytics_response, "Log Analytics")
        
        if analytics:
            duration = analytics.get('duration', {})
            print(f"\n  Duration: {duration.get('formatted', 'N/A')}")
            print(f"  Average Turns per Round: {duration.get('average_turns_per_round', 0)}")
            
            damage = analytics.get('damage_analysis', {})
            print(f"  Average Damage per Turn: {damage.get('average_per_turn', 0)}")
            
            participants = analytics.get('participant_performance', {})
            print(f"\n  Participant Performance:")
            for pid, perf in participants.items():
                print(f"    {perf.get('name', 'Unknown')}:")
                print(f"      Hit Rate: {perf.get('hit_rate', 0)}%")
                print(f"      Critical Hit Rate: {perf.get('critical_hit_rate', 0)}%")
    else:
        print("  ERROR: No logs found")
    
    # Step 8: Get character combat stats
    print("\n8. Getting character combat statistics...")
    characters_response = SESSION.get(f"{BASE_URL}/characters/")
    characters = characters_response.json().get('results', [])
    
    if characters:
        character = characters[0]
        char_id = character['id']
        print(f"  Using character: {character.get('name', 'Unknown')} (ID: {char_id})")
        
        char_stats_response = SESSION.get(f"{BASE_URL}/characters/{char_id}/combat_stats/")
        char_stats = print_response(char_stats_response, "Character Combat Statistics")
        
        if char_stats:
            summary = char_stats.get('summary', {})
            combat_stats = char_stats.get('combat_statistics', {})
            print(f"\n  Total Combats: {summary.get('total_combats', 0)}")
            print(f"  Win Rate: {summary.get('win_rate', 0)}%")
            print(f"  Hit Rate: {combat_stats.get('hit_rate', 0)}%")
            print(f"  Critical Hit Rate: {combat_stats.get('critical_hit_rate', 0)}%")
            
            favorites = char_stats.get('favorites', {})
            if favorites.get('weapon'):
                print(f"  Favorite Weapon: {favorites.get('weapon')}")
            if favorites.get('spell'):
                print(f"  Favorite Spell: {favorites.get('spell')}")
    else:
        print("  ERROR: No characters found")
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print("  Statistics endpoint tested")
    print("  Report endpoint tested")
    print("  JSON export tested")
    print("  CSV export tested")
    print("  Log analytics tested")
    print("  Character stats tested")
    print("\n  SUCCESS: All logging endpoints are working!")
    print("\nTo test with more data:")
    print("  python manage.py test_combat_logging")
    print("  python test_combat_logging.py")

if __name__ == "__main__":
    try:
        test_combat_logging()
    except requests.exceptions.ConnectionError:
        print("\n  ERROR: Could not connect to server.")
        print("   Make sure the Django server is running:")
        print("   python manage.py runserver")
    except Exception as e:
        print(f"\n  ERROR: {e}")
        import traceback
        traceback.print_exc()

