# DnD Combat Simulator – Architecture Blueprint

## 🎯 Goal
Build a SRD 5.2 5e Combat Simulator Web App with structured data, party vs monsters, combat logs, and future analytics.

## 🏗 Tech Stack
- **Backend:** Django + Django REST Framework (DRF)
- **Frontend:** (later) React / Next.js
- **Database:** SQLite (dev) → PostgreSQL (production)

## 📁 Project Structure

dnd_backend/
├─ dnd_backend/ # core settings (settings.py, urls.py, wsgi.py)
├─ bestiary/ # Enemies + Abilities
├─ characters/ # Player characters
├─ items/ # Weapons, armor, consumables
├─ combat/ # Encounters + combat rules (5e)
├─ logs/ # Combat logs & analytics
└─ docs/ # Documentation

## 🌐 API Endpoints
/api/enemies/
/api/abilities/
/api/items/
/api/characters/
/api/encounters/
/api/logs/

## 🧱 Core Models
- **Enemy** (name, hp, ac, attack_bonus, damage, abilities M2M)
- **Ability** (name, description, damage)
- **Character** (name, hp, ac, attack_bonus, damage)
- **Encounter** (M2M characters, M2M enemies)
- **CombatLog** (encounter, message, timestamp)

## ⚔️ Gameplay Rules (SRD 5.2 5e)
- Initiative
- d20 to hit vs AC
- Damage dice rolls
- Turn order
- Abilities/spells
- Combat log for every action

## 🚀 Development Roadmap
✅ Enemy API (you just finished this!)
✅ Admin panel for data entry  
✅ Encounters  
✅ Turn system + dice logic  
✅ Combat log  
✅ React UI (party builder + fight screen)  
✅ Optional login/saves (later)
