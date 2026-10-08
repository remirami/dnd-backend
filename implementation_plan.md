# Master Technical & Feature Plan: 5e Campaign Manager

A comprehensive architectural blueprint and development roadmap for the **5e Campaign Manager**. This document serves as the long-term master reference for core systems, combat mechanics, game modes, AI behavior, and security.

---

## Table of Contents
1. [Executive Pillar Status Dashboard](#executive-pillar-status-dashboard)
2. [Game Modes: Gauntlet Mode vs. Campaign Mode](#1-game-modes-gauntlet-mode-vs-campaign-mode)
3. [Pillar 1: 🏆 Gauntlet Mode (Procedural Wave Survival) [COMPLETED]](#pillar-1--gauntlet-mode-arcade-sandbox-survival-completed)
4. [Pillar 2: 🗺️ Campaign Mode (Persistent RPG Adventure & Leveling) [PLANNED / UPCOMING]](#pillar-2-️-campaign-mode-persistent-rpg-adventure--leveling-planned--upcoming)
5. [Pillar 3: 🔐 Secure Authentication & Account Recovery [COMPLETED]](#pillar-3--secure-authentication--account-recovery-completed)
6. [Pillar 4: 🐉 Monster Abilities Import & Bestiary Schema [COMPLETED]](#pillar-4--monster-abilities-import--bestiary-schema-completed)
7. [Pillar 5: 🧠 Tactical Monster AI Tuning [COMPLETED]](#pillar-5--tactical-monster-ai-tuning-completed)
8. [Pillar 6: 🎯 Advanced Combat: AoE Spells & Movement Economy [COMPLETED]](#pillar-6--advanced-combat-aoe-spells--movement-economy-completed)
9. [Pillar 7: 🧱 Battlefield Obstacles, Cover & Hazards [PLANNED / FUTURE]](#pillar-7--battlefield-obstacles-cover--hazards-planned--future)
10. [Pillar 8: 🗄️ Database Architecture & Production Persistence [COMPLETED]](#pillar-8-️-database-architecture--production-persistence-completed)
11. [Pillar 9: ⚔️ Combat Arena Layout & Ergonomic UX Redesign [COMPLETED]](#pillar-9-️-combat-arena-layout--ergonomic-ux-redesign-completed)
12. [Pillar 10: 🎲 5e Mechanical Correctness & Rules Engine [IN PROGRESS]](#pillar-10--5e-mechanical-correctness--rules-engine-in-progress)
13. [Pillar 11: 🗺️ 2.5D Isometric Combat Grid, Thematic Battlemats & Multi-Tile Tokens [PLANNED]](#pillar-11-️-25d-isometric-combat-grid-thematic-battlemats--multi-tile-tokens-planned)
14. [Long-Term Phased Implementation Roadmap](#12-long-term-phased-implementation-roadmap)
15. [Master Reference Document Status](#13-master-reference-document-status)

---

## Executive Pillar Status Dashboard

| Pillar | Title | Status | Implementation Highlights |
| :--- | :--- | :--- | :--- |
| **Pillar 1** | 🏆 **Gauntlet Mode** | **`✅ COMPLETED`** | Procedural waves 1–10 + endless overtime, inter-wave respite boons, zero-risk snapshot hero isolation (`GauntletSnapshotHero`), scoreboards. |
| **Pillar 2** | 🗺️ **Campaign Mode** | **`⏳ PLANNED / NEXT`** | Node-based adventure map, video-game scaled XP & leveling, interactive level-up wizard, resting sanctuaries. |
| **Pillar 3** | 🔐 **Authentication & Recovery** | **`✅ COMPLETED`** | SimpleJWT HttpOnly cookie refresh tokens, password reset flow (token-based), brute-force rate limiting, automated security test suite. |
| **Pillar 4** | 🐉 **Bestiary & Monster Abilities** | **`✅ COMPLETED`** | Relational `EnemyAction`, `EnemyMultiattack`, regex parser, 2,321 SRD monsters in Neon PostgreSQL, recharge rolls, authentic statblock modal. |
| **Pillar 5** | 🧠 **Tactical Monster AI Tuning** | **`✅ COMPLETED`** | Tactical archetypes (Brute, Skirmisher, Pack Hunter, Caster), multi-factor scoring matrix, autonomous turn resolution with damage flashes. |
| **Pillar 6** | 🎯 **Advanced Combat & AoE Spells** | **`✅ COMPLETED`** | 2D interactive BattleGrid, movement economy, opportunity attacks, visual AoE targeting (Sphere, Cone, Line, Cube), multi-target save resolution. |
| **Pillar 7** | 🧱 **Obstacles, Cover & Hazards** | **`⏳ PLANNED / FUTURE`** | Raycasting line-of-sight, half/three-quarters/full cover, hazard surfaces (lava/acid/spikes), destructible props. |
| **Pillar 8** | 🗄️ **Database & Persistence** | **`✅ COMPLETED`** | PostgreSQL 16 on Neon Cloud Serverless, dual-branching (`dev` & `production`), 28,753 records migrated, sequence resync, in-memory testing. |
| **Pillar 9** | ⚔️ **Combat Arena UX Redesign** | **`✅ COMPLETED`** | Bottom tactical action dock & drawers (Weapons, Spells, Features/Feats, Consumables, Maneuvers), contextual Clash Card, spell slot reset on combat end. |
| **Pillar 10** | 🎲 **5e Mechanical Correctness** | **`🔧 IN PROGRESS`** | Damage type propagation & resistance/immunity/vulnerability engine, spell range validation (Touch/Self/X ft), condition immunity enforcement, enemy action range checks, spell-specific rules lookup table. |
| **Pillar 11** | 🗺️ **2.5D Isometric Combat Grid & Tokens** | **`⏳ PLANNED / SPECIFIED`** | 2.5D angled perspective viewport (45°–60° tilt + 2D toggle), authentic multi-tile token footprints (Large 2×2, Huge 3×3, Gargantuan 4×4), upright billboard standee tokens with depth Z-sorting, thematic high-res battlemats (Crypt, Magma, Colosseum, Bog). |

---

## 1. Game Modes: Gauntlet Mode vs. Campaign Mode

| Feature / Dimension | 🏆 Gauntlet Mode (Arcade Sandbox) | 🗺️ Campaign Mode (Persistent RPG) |
| :--- | :--- | :--- |
| **Core Concept** | High-intensity arcade wave survival in an isolated arena simulation. | Deep narrative / sandbox episodic adventure across fantasy biomes. |
| **Party Size** | **1 to 6 heroes** from player roster. | **1 to 6 heroes** from player roster (or Solo mode with up to 5 recruits). |
| **Encounter Scaling** | Procedural difficulty curve: easy minions $\to$ mixed squads $\to$ mini-bosses $\to$ epic bosses $\to$ endless. | Dungeon / biome node tree with combat, treasure rooms, campsites, and merchants. |
| **Resource Economy** | In-run attrition: HP/spell slots carry wave-to-wave with tactical inter-wave respite boons. | Persistent health, limited Short/Long Rests per chapter, resource conservation. |
| **Character State & Safety** | **Arcade Sandbox**: Snapshot copies used in arena. Character sheets are never permanently harmed or lost. | Persistent character progression: permanent gear, gold, level-ups, and injuries. |
| **Character Leveling** | Fixed level for the run (arcade trial) with run-only boons. | **Video Game Scaled Progression**: Snappy level-ups every 2–3 battles (with future Milestone option). |
| **Loot & Economy** | In-run temporary consumables, boons, and supply drops. | Persistent gold, armor, weapons, magic items, and merchant trading. |
| **Failure State** | Party wipe ends run $\to$ scoreboard tally (waves cleared, kills, turns). | Wipe handling: revival at sanctuary camp with penalty, or retry encounter. |

---

## Pillar 1: 🏆 Gauntlet Mode (Arcade Sandbox Survival) [COMPLETED]

### 1.1 Arcade Sandbox Philosophy
- **Zero Risk, Maximum Tactical Fun**: Characters are entered as **snapshot instances**. Damage taken, expended spell slots, and deaths during the Gauntlet run are completely localized to the arena.
- **Main Character Safety**: When a run ends (by party wipe or voluntary retirement), all participating heroes return to the player's roster completely intact and refreshed.
- **High-Score Prestige**: Focuses on leaderboard metrics: Waves Cleared, Enemies Vanquished, Damage Dealt, and Turns Survived.

### 1.2 Gameplay Loop & Wave Scaling
1. **Party Staging & Dynamic Level Scaling**:
   - Player selects 1 to 6 heroes from their roster.
   - **Party Level Scaling**: The procedural wave generator automatically scales starting enemy CR based on the party's average level:
     - *Level 1–2 Party*: Starts against CR 1/8–1/4 minions (Goblins, Kobolds).
     - *Level 3–4 Party*: Starts against CR 1/2–1 threats (Hobgoblins, Orcs, Bugbears).
     - *Level 5+ Party*: Starts against CR 2–3 threats (Ogres, Manticore, Cult Fanatics).
   - Selects starting arena theme (e.g. *Colosseum of Blades*, *Crypt of the Undead*, *Elemental Spire*).
2. **Procedural Escalation Curve & Wave 10 Climax**:
   - **Waves 1–2 (Warm-up)**: Tier-appropriate fodder and scouts.
   - **Waves 3–4 (Escalation)**: Mixed tactical squads (Brutes + Ranged snipers + Spellcasters).
   - **Wave 5 (Mini-Boss)**: Elite commander with minions + special mechanics.
   - **Waves 6–9 (High Threat)**: High CR predators, apex monsters, and enemy casters.
   - **Wave 10 (Apex Boss Climax)**: Epic boss battle (Dragon, Behir, Archmage) with lair and environmental hazards.
3. **Climax Victory & Endless Overtime Option**:
   - Defeating the Wave 10 Boss officially completes the trial! The player is presented with a Victory screen and two options:
     - 🏆 **Claim Victory & Exit**: Bank run statistics, record high score, and exit to menu with full honors.
     - ⚔️ **Continue into Endless Overtime**: Push beyond Wave 10 into infinite waves with procedurally boosted enemy stats (+HP, +damage, elite modifiers) for legendary high-score bragging rights.
4. **Inter-Wave Respite Screen**:
   Between waves, before the next encounter spawns, player selects **one** tactical bonus:
   - 🩹 **Take a Breather**: Spend 1–2 Hit Dice to recover HP.
   - 🔮 **Arcane Surge**: Regain one expended spell slot.
   - 🧪 **Supply Drop**: Gain a Potion of Healing or combat scroll.
   - ⚡ **Combat Boon**: Temporary buff for the next wave (+2 AC, +10 ft speed, or Advantage on first attack).
5. **Scoring & Leaderboards**:
   - Tracks: Waves Cleared (Standard vs. Endless), Total Damage Dealt, Enemies Vanquished, Turns Survived.

---

## Pillar 2: 🗺️ Campaign Mode (Persistent RPG Adventure & Leveling) [PLANNED / UPCOMING]

### 2.1 Gameplay Loop & Progression
1. **Campaign Creation & Party Embarkation**:
   - Player creates a Campaign, choosing a primary Biome (Forest, Desert, Mountain, Swamp, Underdark).
   - Assembles a party of **1 to 6 heroes** (or Solo mode starting with 1 character and recruiting up to 5 companions).
2. **Node-Based Adventure Map**:
   - Procedural or hand-crafted node tree:
     - ⚔️ **Combat Encounters**: Standard, ambush, or elite battles.
     - 💎 **Treasure Rooms**: Locked chests, gold hoards, and gear upgrades.
     - ⛺ **Campsites**: Safe zones for Short Rests and Long Rests.
     - 🛒 **Wandering Merchants**: Buy potions, scrolls, and upgraded equipment.
     - 👑 **Chapter Boss**: Climax encounter guarding the passage to the next region.
3. **Video Game Scaled Leveling System**:
   - **Pacing Calibration**: Rather than the slow grind of tabletop 5e rules (which requires dozens of sessions to level up), leveling is calibrated for a snappy, rewarding video game pace: **approximately 1 Level Up every 2 to 3 completed encounters** (or ~1 Level Up per dungeon floor/chapter).
   - **Scaled XP Curve**:
     - Encounter XP rewards are scaled dynamically based on battle difficulty to deliver regular, satisfying level-ups:
       - Level 1 $\to$ 2: 100 XP (~1–2 battles)
       - Level 2 $\to$ 3: 250 XP (~2 battles)
       - Level 3 $\to$ 4: 450 XP (~2–3 battles)
       - Level 4 $\to$ 5: 700 XP (~3 battles)
       - Continuous smooth scaling up to Level 20.
   - **Pluggable Milestone Progression Option**:
     - The architecture includes a clean progression toggle: `PROGRESSION_MODE = 'video_game_xp' | 'milestone'`.
     - In **Milestone Mode**, numerical XP calculations are bypassed. Level-ups are granted automatically upon completing key story milestones (e.g. defeating a mini-boss, clearing a dungeon floor, or conquering a chapter boss).
     - Both systems funnel into the identical **Interactive Level-Up Wizard**.
4. **Interactive Level-Up Wizard (Frontend UI)**:
   - When a character earns a level up, a prominent, animated **"Level Up Ready!"** badge appears on their portrait.
   - Clicking opens the interactive wizard guiding the player through:
     - **Hit Point Increase**: Choose between rolling hit die or taking standard average + CON modifier.
     - **Spell Slots**: Visual grid showing newly unlocked spell slot tiers.
     - **Subclass Selection**: Prompts at class milestone (Level 2 for Cleric/Druid/Wizard; Level 3 for Fighter, Rogue, Paladin, etc.) with feature descriptions.
     - **Class Features**: Automatic awarding of new class abilities (Action Surge, Extra Attack, Cunning Action).
     - **Ability Score Improvement (ASI) / Feats**: Interactive point allocator (+2 to one stat or +1 to two stats) at Levels 4, 8, 12, 16, 19.
5. **Rest & Recovery Mechanics**:
   - **Short Rest**: Spend available Hit Dice pools to regain HP. Recovers short-rest resources (Warlock pact slots, Fighter Action Surge & Second Wind, Monk Ki).
   - **Long Rest**: Limited to available campsite tokens (e.g. 2 per chapter). Fully restores HP, Hit Dice (up to half max), and all spell slots; resets all daily class abilities.
6. **Hero Defeat & Camp Sanctuary System**:
   - **Camp Sanctuary (Default Rule)**: If a character drops to 0 HP and fails 3 death saves during a campaign encounter, they are knocked out for the duration of that battle. Upon returning to camp, they can be revived through resting, healer provisions, or a modest gold/remedy fee.
   - *Future Permadeath Option*: Designed with an extensible schema to support an optional **Permadeath / Ironman Mode** campaign modifier in a future update for hardcore players.
7. **Simultaneous Multi-Mode Usage**:
   - Characters are **never locked** to a single mode.
   - The same hero can actively explore a Campaign, jump into an Arcade Gauntlet wave run, or test combat maneuvers simultaneously.
   - The Campaign system maintains its own isolated snapshot tracking (CampaignCharacter: current HP, temp HP, spell slots, and chapter XP) so external play never corrupts or blocks campaign progress.

---

## Pillar 3: 🔐 Secure Authentication & Account Recovery [COMPLETED]

### 3.1 Current State & Identified Gaps
- Currently uses JWT via `rest_framework_simplejwt` with username/password.
- **Gaps**: No password reset flow, no email recovery mechanism, refresh tokens are not rotated or blacklisted, no brute-force lockout, and passwords lack complexity enforcement.

### 3.2 Target Security Architecture
1. **Account Recovery & Password Reset Flow**:
   - **Request Reset**: `POST /api/auth/password-reset/` accepts username or email. Generates a secure, cryptographically signed one-time token with a 15-minute expiration (`django.contrib.auth.tokens.default_token_generator`).
   - **Verification & Reset**: `POST /api/auth/password-reset/confirm/` accepts token, UID, and new password. Validates token authenticity, updates password hash (PBKDF2/Argon2), and invalidates existing sessions.
   - **Email / Dev Mode Support**:
     - Development: Logs the reset link/token directly to console and returns safe dev confirmation.
     - Production: Integrates standard SMTP / transactional email provider (e.g. SendGrid, SES, Resend).
   - **Frontend UI**:
     - `/forgot-password` request view.
     - `/reset-password?token=...&uid=...` password reset submission view.
2. **Token Security & Session Management**:
   - **Refresh Token Rotation**: SimpleJWT configured with `ROTATE_REFRESH_TOKENS = True` and `BLACKLIST_AFTER_ROTATION = True`. Any replay of a used refresh token triggers immediate invalidation of the entire token family.
   - **Storage Strategy**: Transition from plain `localStorage` to `HttpOnly`, `Secure`, `SameSite=Lax` cookies for the refresh token to mitigate XSS exposure.
   - **Session Expiry & Heartbeat**: Frontend auth store tracks token lifetime with seamless background refresh.
3. **Defense-in-Depth Measures**:
   - **Brute Force Throttling**: Dedicated DRF throttle on `/api/auth/login/` (e.g. 5 failed login attempts locks IP/account for 15 minutes).
   - **Password Strength Rules**: Enforce minimum 8 characters, alphanumeric + special characters using Django `AUTH_PASSWORD_VALIDATORS`.
   - **Profile Management**: Endpoints for `POST /api/auth/change-password/` (requiring current password verification) and `PATCH /api/auth/profile/`.

---

## Pillar 4: 🐉 Monster Abilities Import & Bestiary Schema [COMPLETED]

### 4.1 Current State & Identified Gaps
- `bestiary/models.py` contains basic stats (`EnemyStats`) and simple attacks (`EnemyAttack` with plain string damage).
- Complex 5e monster abilities (Multiattack variations, Breath Weapons, Legendary Actions, Condition applications, Spellcasting) are stored as raw descriptive strings (`EnemyAbility.description`) that the combat engine cannot execute programmatically.

### 4.2 Comprehensive Monster Action Schema
Refactor and expand the `bestiary` models to make monster actions fully executable:

```
bestiary/models.py
├── Enemy
│   ├── stats (EnemyStats: STR, DEX, CON, INT, WIS, CHA, Speed, Senses)
│   ├── actions (EnemyAction)
│   │   ├── action_type: ['action', 'bonus_action', 'reaction', 'legendary_action']
│   │   ├── attack_type: ['melee_weapon', 'ranged_weapon', 'melee_spell', 'ranged_spell', 'saving_throw', 'utility']
│   │   ├── attack_bonus: int (+5 to hit)
│   │   ├── reach_or_range: (reach: 5 ft, range: 60/120 ft)
│   │   ├── damage_rolls (EnemyActionDamage)
│   │   │   ├── dice_count, dice_sides, damage_bonus, damage_type
│   │   ├── saving_throw_dc: int (e.g. DC 15 DEX save)
│   │   ├── saving_throw_ability: ['STR', 'DEX', 'CON', 'INT', 'WIS', 'CHA']
│   │   ├── half_damage_on_save: bool
│   │   ├── conditions_inflicted (ManyToManyField Condition: Grappled, Poisoned, Prone, Paralyzed)
│   │   ├── condition_save_end: bool (can repeat save at end of turns)
│   │   └── recharge_mechanic:
│   │       ├── has_recharge: bool
│   │       ├── recharge_die: int (e.g. d6)
│   │       ├── recharge_min_roll: int (e.g. 5-6)
│   │       └── is_charged: bool
│   ├── multiattack_rules (EnemyMultiattack)
│   │   └── sequence: JSON (e.g. [{"action": "Bite", "count": 1}, {"action": "Claw", "count": 2}])
│   ├── traits (EnemyTrait: Pack Tactics, Magic Resistance, Undead Fortitude, Spider Climb)
│   └── legendary_actions (3 points per round, costs 1-3 points per action)
```

### 4.3 Automated SRD Data Import Pipeline & Structured Parser [COMPLETED]
- Executed `python manage.py parse_existing_monsters --clear-existing` across all 315 SRD monsters.
- Transformed unstructured string abilities and attacks into fully relational models:
  - **1,059 Structured Enemy Actions** (melee, ranged, saving throw, utility, bonus action, and legendary action records).
  - **788 Damage Roll Formulas** linked with authentic damage types (e.g. `12d8 acid`, `2d10+6 piercing`).
  - **134 Multiattack Sequences** with sequence breakdowns and action counts.
  - **835 Special Traits** categorized by trait type (`pack_tactics`, `undead_fortitude`, `nimble_escape`, `legendary_resistance`, etc.).
  - **112 Legendary Actions** synchronized across both `EnemyAction` and `EnemyLegendaryAction`.

### 4.4 Dedicated Standalone Bestiary Compendium (`/bestiary`) & Dashboard Placement
*Elevate monster inspection from an in-combat modal into a first-class compendium browser.*

1. **Dashboard Placement (Dual-Tome Lower Grid)**:
   - Preserves the sacred **Three Pillars** on the main dashboard (`CHARACTERS`, `COMBAT ARENA`, `GAUNTLET`).
   - Transforms the lower-left informational parchment scroll ("The Realm Companion") into **"The Bestiary & Monster Archives"** parchment tome.
   - Symmetrically balances the **Chronicles (Recent Updates)** card on the right, providing two thematic reference codices at the bottom of the realm portal.
   - Displays real-time catalog stats: "2,321 SRD Beasts & Adversaries", category tag teasers (Dragons, Undead, Fiends, Beasts), and a direct action link: `✦ OPEN THE BESTIARY ARCHIVES → ✦`.

2. **Compendium Browser Features (`/bestiary`)**:
   - **Multi-Attribute Filter Bar**:
     - Challenge Rating (CR 0 to CR 30 with fractional CR 1/8, 1/4, 1/2 support).
     - **Parchment Statblock View**: Full 5E statblock styling with ability scores, saving throws, damage resistances/immunities, traits, multiattack routines, and action breakdown with dice formula tooltips.

---

## Pillar 5: 🧠 Tactical Monster AI Tuning [COMPLETED]

### 5.1 Tactical Behavioral Archetypes
Replace simple random/lowest-HP attacks with distinct tactical AI profiles:

1. **The Brute / Frontliner (Ogre, Bugbear, Minotaur)**:
   - Prioritizes closing distance to the closest enemy.
   - Uses special maneuvers when available: Shove/Knock Prone, Grapple, Reckless Attack.
   - Focuses down frontline warriors.
2. **The Skirmisher / Ambusher (Goblin, Kobold, Bandit)**:
   - Uses ranged attacks from cover.
   - Employs Bonus Action mobility: Nimble Escape / Cunning Action (Disengage or Hide).
   - Kites away from melee combatants to maintain distance.
3. **The Pack Hunter (Wolf, Dire Wolf, Gnoll)**:
   - Targets creatures already engaged with an ally to exploit **Pack Tactics** (Advantage on attack rolls).
   - Concentrates fire on isolated or prone targets.
4. **The Tactical Caster (Mage, Cult Fanatic, Priest)**:
   - Pre-casts or maintains defensive spells (Mage Armor, Shield on reaction, Blur).
   - Evaluates player clustering to place AoE spells (Fireball, Shatter) maximizing targets while avoiding friendly fire.
   - Maintains line-of-sight while ducking behind cover.
   - Retreats when threatened in melee.
5. **The Apex / Boss (Dragons, Beholders, Vampires)**:
   - Manages **Recharge Abilities**: Uses breath weapon as soon as available; falls back on multiattack while cooling down.
   - Weaves **Legendary Actions** between player turns (e.g. Wing Attack at end of a Fighter's turn to reposition).
   - Disrupts player concentration by targeting concentrating spellcasters.

### 5.2 Turn Decision Matrix
Each monster turn evaluates:
1. **Self-Preservation**: If HP $< 20\%$ and cowardly archetype $\to$ Disengage and flee or seek cover.
2. **Recharge Check**: Roll d6 at turn start for abilities with recharge (e.g. 5–6).
3. **Target Evaluation Score**:
   $$\text{Score} = w_1 \cdot (1 - \frac{\text{Current HP}}{\text{Max HP}}) + w_2 \cdot \text{Is Concentrating} + w_3 \cdot \text{Proximity} + w_4 \cdot \text{Can Trigger Pack Tactics}$$
4. **Action Execution**: Execute highest-impact available action (AoE $\to$ Multiattack $\to$ Single attack $\to$ Dash/Reposition).

### 5.3 Monster Actions & Tactical Traits Engine [COMPLETED]
- **Phase 1 Completed (Structured Monster Data Pipeline & Bestiary Modal Display)**:
  - 315 SRD monsters parsed into structured `EnemyAction`, `EnemyActionDamage`, `EnemyTrait`, `EnemyMultiattack`, and `EnemyLegendaryAction` relational records.
  - Interactive bestiary stat block modal displays formatted damage rolls, reach/range, saving throw DCs, and legendary point costs with authentic parchment styling.
- **Phase 2 Completed (Combat Engine AoE & Saving Throw Actions)**:
  - Turn-start 1d6 recharge rolls re-enable `has_recharge=True` actions when roll $\ge$ `recharge_min_roll` (5–6) with automatic `CombatAction` event logging.
  - Multi-target AoE and breath weapons support `target_ids` batch execution with DC saving throws, half damage on save, and condition rider applications.
  - Damage resistances/immunities integrated into saving throw damage resolution via `target.take_damage(damage_type=...)`.
  - Action economy enforcement: `action_used = True`, `attacks_remaining = 0`, and `recharge_state[action_name] = False`.
- **Phase 3 Completed (Tactical Monster Traits)**:
  - **Pack Tactics**: Advantage calculation based on ally engagement ($\le 5\text{ ft}$) and intelligent target swarming (+25 focus).
  - **Nimble Escape**: Goblin / skirmisher bonus action Disengage and tactical repositioning away from melee threats.
  - **Undead Fortitude**: Zombie CON save ($5 + \text{damage taken}$) on lethal damage to remain at 1 HP, bypassed by radiant damage and critical hits.
  - **Legendary Resistance (3/Day)**: Boss monsters automatically convert failed saving throws into successes with charge tracking and combat notices.
- **Phase 4 Completed (Legendary Action Weaving & Dynamic Reaction Triggers)**:
  - **Legendary Action Weaving**: Bosses weave actions (`execute_ai_legendary_action`) between participants at the conclusion of other creatures' turns (`next_turn`). Supports Cost 2 Wing Attack (AoE DEX save, knock prone, tactical repositioning) and Cost 1 Tail Attacks, spending points from the 3-point pool. Points reset at the start of the boss's own turn.
  - **Defensive Shield Reaction**: Enemy spellcasters with Shield dynamically react when incoming attack rolls would hit, gaining $+5$ AC to turn hits into misses (`reaction_used = True`, `shield_spell_active = True`).
  - **Grid-Based Opportunity Attacks**: Non-disengaging participants moving away from enemy reach trigger tactical opportunity attacks along the path.
- **Verification**: 15/15 tests passing in `combat.test_monster_actions`, 78/78 tests passing in `combat`, and Next.js frontend builds cleanly with 0 errors.

---

## Pillar 6: 🎯 Advanced Combat: AoE Spells & Movement Economy [COMPLETED]

### 6.1 Interactive 2D Battlemap Grid
- **Grid Layout**: Standard 5-foot squares (e.g. 20×20 or 24×16 grid).
- **Combatant Tokens**: Display miniature avatar, HP bar, AC badge, and condition icons.
- **Coordinates**: Each `CombatParticipant` maintains `(position_x, position_y)` coordinates in feet (increments of 5).

### 6.2 Movement Economy & Opportunity Attacks
1. **Movement Budget**:
   - Each turn tracks `movement_used` vs. `speed` (typically 30 ft = 6 squares).
   - Frontend highlights walkable squares in blue (walkable) and yellow (requires Dash action).
2. **Difficult Terrain**:
   - Squares marked as rubble, mud, or water cost 10 ft of movement per 5 ft moved (2× cost).
3. **Opportunity Attacks**:
   - When a combatant moves out of an opponent's melee reach (typically 5 ft) without using the **Disengage** action, triggers an immediate Opportunity Attack reaction prompt from the engaged enemy.

### 6.3 AoE Targeting & Multi-Target Resolution
1. **Visual Target Overlays**:
   - **Sphere**: Circle overlay centered on target point (e.g. Fireball: 20 ft radius = 4 squares).
   - **Cone**: 53-degree wedge projected from caster in chosen direction (e.g. Burning Hands: 15 ft cone).
   - **Line**: Rectangle originating from caster (e.g. Lightning Bolt: 100 ft × 5 ft).
   - **Cube / Cylinder**: Square footprint overlay.
2. **Target Highlighting & Friendly Fire**:
   - Live canvas detects all combatants whose token boundaries intersect the shape.
   - Color-codes targets: **Red** (enemies in blast), **Amber/Green** (allies in blast with prominent Friendly Fire Warning).
3. **Automated Save & Damage Pipeline**:
   - Auto-rolls saving throws for every affected creature against the caster's Spell Save DC ($8 + \text{proficiency} + \text{ability mod}$).
   - Computes:
     - Full damage on failed save.
     - Half damage on successful save (or 0 damage for creatures with Evasion).
     - Damage resistances / immunities applied per target.
   - Comprehensive combat log records every save result and damage dealt.

### 6.4 Player Reaction Prompts & Combat Speed Controls
1. **Interactive Player Reaction Prompts**:
   - When a battlefield trigger occurs that activates a character's reaction:
     - **Opportunity Attack**: Enemy flees melee reach without Disengage $\to$ prompt asks `[⚔️ Strike]` or `[Pass]`.
     - **Defensive Spells**: Triggered on incoming hit (e.g. *Shield* $+5$ AC, *Absorb Elements*, or *Hellish Rebuke*).
     - **Counterspell**: Triggered when an enemy caster within 60 ft begins casting.
   - The combat engine pauses and displays an intuitive pop-up prompt with action description and decision buttons. Includes a brief optional timer to maintain snappy combat flow.
2. **Combat Animation Speed Toggle**:
   - Header HUD features a persistent speed controller:
     - **`1x Normal`**: Standard pacing with dice roll animations, movement transitions, and floating damage numbers.
     - **`2x Fast`**: Accelerated animations for quick turns.
     - **`⚡ Instant`**: Bypasses movement delays and rolls immediately; perfect for blazing through large enemy mob turns.

---

## Pillar 7: 🧱 2.5D Isometric Combat Grid & Environmental Arena System [PLANNED / FUTURE]

### 7.1 2.5D Isometric & Angled Viewport
1. **Camera Perspective Projection**:
   - Tilting perspective (e.g. 45°–60° pitch, subtle isometric rotation) to introduce true battlefield depth while strictly maintaining discrete 5-foot tile-based Chebyshev movement `(x, y)`.
   - **Dual-View Toggle**: HUD switcher between **Top-Down 2D** (pure tactical overview) and **2.5D Angled Overview** (cinematic depth).
   - Smooth pan and zoom controls for large battlefields.
2. **Upright 2.5D Billboard Tokens**:
   - Miniature tokens, monster portraits, and spell markers stand upright facing the camera (billboard orientation).
   - Grounded perspective drop-shadows anchored directly to floor tiles to indicate position, elevation, or flight.
   - Active turn aura rings and selection borders projected flat on the floor underneath upright tokens.

### 7.2 Custom & Environmental Grid Geometries (Non-Rectangular Arenas)
1. **Beyond Rigid Rectangles**:
   - Replaces static N×M rectangular boxes with organic, tactical battlefield layouts:
     - **Chokepoint Corridors**: Narrow 1–2 tile dungeon hallways and cavern tunnels.
     - **Circular Arenas & Colosseums**: Radial or polygonal fighting pits with perimeter boundary walls.
     - **Chasms & Ravines**: Impassable void gaps between stone platforms that require jump mechanics, spells, or bridges to cross.
     - **L-Shaped & Multi-Room Layouts**: Connected chambers with door transitions and vision obstruction.
2. **Dynamic Tile Matrix States**:
   - Every tile in the arena evaluates: `Walkable`, `Void / Pit`, `Difficult Terrain` (2x cost), `Hazard` (Lava/Acid), and `Wall / Obstacle`.

### 7.3 Thematic Biome Backgrounds & Textures
1. **Biome-Specific Battlemats**:
   - *Crypt of the Undead*: Cracked ancient stone slabs, cobwebs, dark moss, bone piles.
   - *Infernal Pit*: Volcanic basalt rock with glowing magma channels and embers.
   - *Colosseum of Blades*: Blood-stained sand with wooden boundary fences and spectator railings.
   - *Sunken Dungeon / Cavern*: Wet stone reflections, puddles, stalagmites.
   - *Savage Wilds*: Dirt path, dense foliage borders, fallen logs.
2. **Atmospheric Effects & HUD Controls**:
   - Layered atmospheric particles (dust motes, smoke, torchlight vignettes).
   - Grid line opacity slider (10% to 100%) allowing players to prioritize environmental immersion or tactical precision.

### 7.4 Cover System, Line-of-Sight & Interactive 2.5D Props
1. **Raycasting Line of Sight**:
   - Evaluates straight-line rays from attacker token center to the 4 corners of the target token.
2. **Tactical Cover Tiers**:
   - **Half Cover (+2 AC, +2 DEX saves)**: Low stone walls, crates, barrels, overturned tables, or intervening creatures.
   - **Three-Quarters Cover (+5 AC, +5 DEX saves)**: Portcullises, thick stone pillars, statue pedestals, arrow slits.
   - **Full Cover (Cannot be directly targeted)**: Heavy masonry walls, closed dungeon doors.
3. **Interactive Battlefield Props**:
   - Destructible props with AC and HP (wooden doors, barricades).
   - Interactive manipulation: opening/closing doors, climbing onto elevated ledges, pushing enemies into hazard zones.

---

## Pillar 8: 🗄️ Database Architecture & Production Persistence [COMPLETED]

### 8.1 Why a Production Database is Required
Currently, development operates on a local file-based SQLite database (`db.sqlite3`). While SQLite enables quick offline bootstrapping, transitioning the 5e Campaign Manager to a reliable, scalable system requires a production database architecture due to several critical constraints:

1. **High Concurrency & Combat Turn Collisions**:
   - In real-time tactical combat, multiple combatants (players and AI threads), reactions, and background WebSocket sync loops make simultaneous writes.
   - SQLite uses file-level locking, resulting in `OperationalError: database is locked` during concurrent combat updates. Production systems require **row-level locking** (`select_for_update`) so atomic HP changes, spell slot deductions, and reaction prompts occur without race conditions or locks.
2. **Dynamic JSON Schemas & Deep D&D Data Structures**:
   - D&D 5e features complex nested schemas: spell slot trackers (`{"1": {"total": 4, "used": 1}}`), paperdoll equipment slots, dynamic ability bonuses, and environmental hazard coordinates.
   - Requires native binary JSON indexing (`JSONB` with GIN indexes) for rapid querying, filtering, and atomic field modifications without pulling the entire record into Python memory.
3. **Massive Relational Catalog**:
   - Over 3,200+ Bestiary monsters, 300+ spells, items, feats, and character progression trees require strict ACID foreign keys, cascade safety, and fast relational joins (`select_related` / `prefetch_related`).
4. **Single-Player Architecture Simplicity**:
   - Because each user plays their own campaign/gauntlet independently without multiplayer room broadcasting, all combat actions (player attacks, enemy AI turns, leveling) flow cleanly through standard HTTP REST requests (`/attack/`, `/next_turn/`, `/ai_turn/`).
   - Standardizing on a single production database avoids the operational burden of extra broker containers, separate caching clusters, and distributed sync bugs.

---

### 8.2 Database Architecture & Recommendations

```mermaid
graph TD
    subgraph Client Tier
        FE[Next.js 16 Frontend / React 19]
    end

    subgraph Application Tier
        API[Django REST API / Gunicorn]
    end

    subgraph Data Tier
        PG[(PostgreSQL 16 - Primary RDBMS)]
    end

    FE -->|HTTP / REST API (Attacks, Turns, Leveling)| API
    API -->|Read/Write ORM (JSONB, ACID, Foreign Keys)| PG
```

#### 1. 🐘 Primary Database: PostgreSQL 16+ (The Only Production Database Needed)
- **Why PostgreSQL is Sufficient**:
  - **Native Django ORM Integration**: First-class support; already provisioned in `requirements.txt` (`psycopg2-binary`).
  - **Row-Level Concurrency (`select_for_update`)**: Guarantees atomic transaction isolation during turns, reaction triggers, and HP changes.
  - **Postgres `JSONB` & GIN Indexes**: Fast indexing of character sheet sub-attributes, spell slot maps (`{"1": {"total": 4, "used": 1}}`), and monster action definitions.
  - **Built-in Full-Text Search (FTS)**: Built-in `django.contrib.postgres.search` (`SearchVector`, `TrigramSimilarity`) to power instant search across 3,200+ monster names, spell descriptions, and items without needing Elasticsearch or separate search clusters.
  - **Recommended Hosting / Providers**:
    - **Cloud Managed (Serverless)**: **Supabase** or **Neon** (generous free tiers, built-in connection pooling, instant backups).
    - **Self-Hosted / Traditional Cloud**: **Railway**, **Render**, or a local **Docker Compose** container (`postgres:16-alpine`).

#### 2. 💡 Why Redis is NOT Needed for this Single-Player Architecture
- **No Multiplayer Interaction**: Since players do not share combat rooms or chat sessions, there is no need for a distributed pub/sub broker (`channels-redis`) to push messages across different worker processes.
- **REST-Driven Combat State**: The Next.js frontend calls REST API endpoints (`/attack/`, `/ai_turn/`, `/auto_enemy_turns/`) and updates local state directly from the JSON responses.
- **Zero Cost & Minimal Maintenance**: Omitting Redis eliminates an entire running container in dev, saves hosting costs in cloud production (e.g. paying for an extra Redis node on Render/AWS), and prevents connection dropouts.
- **In-Memory Caching Alternative**: If caching static SRD monsters or spells is ever needed, Django's built-in `LocMemCache` (local in-memory cache) or `DatabaseCache` provides sub-millisecond caching directly inside the Python process with zero extra infrastructure.

#### 3. 🧪 Testing / CI Runner: SQLite (Retained)
- SQLite remains configured strictly for local unit testing (`python manage.py test`) and GitHub Actions CI runs, providing instant in-memory `:memory:` databases without spin-up overhead.

#### 4. 🚀 Provisioned Neon Infrastructure & Branching Setup (Option 1 Selected)
- **Project ID**: `fancy-lake-60243378` (`5eManager`), Org: `org-purple-hall-37246432`
- **Region**: AWS Frankfurt (`eu-central-1`)
- **Branch Strategy**:
  - `dev` branch: Dedicated cloud development database used by local developers (`.env`).
  - `production` branch: Dedicated production database reserved for cloud deployment (Render).
- **Environment Templates**:
  - `.env`: Configured with Neon `dev` pooled connection URL.
  - `.env.production.example`: Provided for Render pointing to Neon `production` branch.

---

### 8.3 Data Migration & Transition Strategy (`db.sqlite3` $\to$ PostgreSQL) - COMPLETED

1. **Schema & Field Length Alignment**:
   - Expanded field constraints to safely accommodate long Open5e text sizes without truncation (`DamageType.name`, `Language.name`, `EnemyAttack.name`, `EnemyAbility.name`, `EnemyLegendaryAction.name`, `Weapon.weapon_type`, `Spell.casting_time`).
   - Applied migrations to Neon: `python manage.py migrate`.
2. **Direct High-Speed Bulk Migration**:
   - Built a high-performance direct migration pipeline transferring all 28,753 application records from SQLite to Neon in 143 seconds.
   - Preserved all foreign keys, many-to-many through tables, and multi-table inheritance relationships.
3. **Primary Key Sequence Resynchronization**:
   - Resynced all 67 PostgreSQL primary key sequences via `sqlsequencereset`.
4. **Automated Verification**:
   - Verified system check (0 issues).
   - Verified data integrity across monsters, characters, spells, attacks, and items.
   - Ran 420 automated unit tests in-memory (`Ran 420 tests in 81.3s - OK`).

---

## 9. Frontend Architecture & Master Layout Overhaul Plan

Based on the verified UI mockups and design references, a full layout overhaul is specified with an antique dark-and-gold D&D 5e theme:

### 1. Official Color Palette & Design Tokens
- **Background (`#0c0d12`)**: Deep obsidian midnight backdrop.
- **Card Surfaces (`#181a21`)**: Dark charcoal slate used for primary interactive cards (Characters, Campaign, Gauntlet, Character stat cards, Changelog).
- **Golden Trim & Accents (`#c5a059`)**: Antique warm gold used for borders, serif titles, icons, and decorative corner tabs.
- **Golden Glow (`rgba(197, 160, 89, 0.25)`)**: Ambient glow around active and hovered cards.
- **Changelog Typography (`#d1cdb8`)**: Parchment light beige for changelog bullet points and descriptive body copy.
- **Version Accent (`#a63a3a`)**: Deep crimson red used for changelog version tags (e.g. `v1.7.0`) and health danger states.
- **HP Accent (`#22c55e` / `#16a34a`)**: Vibrant green for current hit points (`15/15`).
- **Footer / Legal Text (`#404552`)**: Subtle dark slate for legislative licensing text.

### 2. Typography Hierarchy
- **Google Font `Cinzel Decorative` (`font-cinzel-decorative`)**:
  - Dashboard logo (`5E DASHBOARD`).
  - Three main action pillar card titles (`CHARACTERS`, `CAMPAIGN`, `GAUNTLET`).
  - Characters page headline (`MY CHARACTERS`).
- **Google Font `Lora` (`font-lora`)**:
  - Account dropdown menu (`JUKKA`, `Logout`).
  - Main card interactive tooltips / descriptive sub-cards (`✦ MANAGE HEROES ✦`, etc.).
  - Changelog title & body copy (bold header, regular body).
  - Characters card text, descriptions, and titles.
  - Footer legislative / legal license disclaimer.
- **Google Font `Fira Sans` (`font-fira-sans`)**:
  - Clean, high-legibility numerical readouts and stats on the Characters page (`Hit points: 15/15`, `Armour Class: 14`, `Wealth: 100g`, level tags).

### 3. Core Layout Components

#### A. Main Dashboard (`/`)
- **Top Header**:
  - Centered golden title: `5E DASHBOARD` in Cinzel Decorative.
  - Top-right user circle icon: Clicking reveals a sleek dropdown menu in Lora showing the authenticated user's name (e.g. `JUKKA`) and a `Logout` action (triggering blacklisting and HttpOnly cookie clearance).
- **The Three Pillars (Interactive Cards)**:
  1. **CHARACTERS**: Robed Adventurer icon (`#c5a059`), golden corner brackets, sub-card: `✦ MANAGE HEROES ✦` ("View your adventurers, their gear, and attributes.").
  2. **CAMPAIGN**: Swords & Shield Emblem icon (`#c5a059`), golden corner brackets, sub-card: `✦ ENTER THE ARENA ✦` ("Initiate the combat simulator. Track initiative order, manage hit points, and roll the dice to determine the fates of battle.").
  3. **GAUNTLET**: Crowned Skull icon (`#c5a059`), golden corner brackets, sub-card: `✦ FACE THE CHALLENGE ✦` ("Test your heroes' endurance in the merciless Gauntlet. How many waves of monsters can you survive in the depths of the dungeon?").
  - *Corner Styling*: Distinctive antique gold corner tab ears extending on all 4 corners of each card.
  - *Tooltip Implementation*:
    - Built using smooth CSS/Radix hover micro-interactions anchored directly beneath each card.
    - On hover/focus (desktop), slides down with a gentle fade (`transition-all duration-200`) showing the dark card with crimson border `#a63a3a`, parchment text `#d1cdb8` in Lora, and diamond headers.
    - On touch devices (mobile/tablet), tapping once expands the tooltip info; tapping again or pressing the action navigates to the page.
- **The Dual-Tome Lower Grid (Reference Codices)**:
  - **Left Tome**: **The Bestiary & Monster Archives Parchment Scroll** (`ParchmentScroll.tsx`):
    - Replaces the static welcoming text with an active compendium gateway.
    - Header: `MONSTER ARCHIVES` with antique wax seal stamp and golden filigree divider.
    - Real-time catalog summary: "2,321 SRD Beasts & Adversaries from Open5e".
    - Quick category chips (Dragons, Fiends, Undead, Beasts) and prompt link navigating directly to `/bestiary`.
  - **Right Tome**: **The Chronicles (Changelog Card)** (`FantasyCard.tsx`):
    - Header: `Chronicles` with version tag `v1.13.1` in crimson `#a63a3a` (Lora bold).
    - Bulleted release ledger in parchment `#d1cdb8` with link to full `/changelog`.
- **Footer**:
  - Required Wizards of the Coast SRD 5.1 / 5.2 Creative Commons CC-BY-4.0 attribution and trademark notice in `#404552` (Lora).

#### B. Characters View (`/characters`)
- **Top Navigation Bar**:
  - Left: `5E DASHBOARD` logo link (Cinzel Decorative).
  - Center buttons with golden borders: `Home`, `Quick Random`, `Create character` (Lora).
  - Right: User account circle avatar with Lora dropdown menu.
- **Page Title**: `MY CHARACTERS` in gold Cinzel Decorative.
- **Character Grid (2-column responsive layout)**:
  - Gold border `#c5a059` on `#181a21` background.
  - Header row: Character Name (`Roderick` in Lora) on left, Level (`Lvl 1` in Fira Sans) on right.
  - Subtitle: Race & Class (`Human paladin` in Lora).
  - Stat Rows (Fira Sans for crisp stat legibility):
    - `Hit points`: `15/15` (green value `#22c55e`).
    - `Armour Class`: `14`.
    - `Wealth`: `100g`.

---

---

## Pillar 9: ⚔️ Combat Arena Layout & Ergonomic UX Redesign [COMPLETED]

### 9.1 The Problem: Clunky Utilitarian Arena
The current `/combat/[id]` combat simulator and arena layout operates on a rigid two-column desktop split that feels clunky, utilitarian, and cluttered during active play:
- The left column is split between a tall initiative order list and a static combat log box.
- The right column is a towering stack: incapacitation banners, attacker badges, target selectors, weapon buttons, spell grids, and testing tabs requiring constant vertical scrolling.
- Vital information is scattered across distant screen corners, making turn execution feel disjointed rather than snappy and tactical.
- On standard displays or mobile viewports, vertical scrollbars cause layout jitter, clip buttons, and obstruct action flows.

### 9.2 Target Design Architecture: Streamlined Tactical HUD
Inspired by modern tactical RPGs (Baldur's Gate 3, Solasta: Crown of the Magister, Darkest Dungeon II), the redesigned arena will be built around player ergonomics, action availability, and immediate battlefield visibility:

1. **Ergonomic Bottom Tactical Action Dock**:
   - Replaces the right-column stack with a sleek, docked bottom hotbar featuring categorized quick-access tabs:
     - ⚔️ **Weapons & Attacks**: Grid of equipped weapons with damage formulas, to-hit bonuses, and reach indicators.
     - 🔮 **Spells & Cantrips**: Tiered spell selection with spell slot counter pips and upcasting controls.
     - 🛡️ **Tactical Maneuvers**: Dash, Disengage, Dodge, Hide, Help, and Opportunity reactions.
     - 🧪 **Items & Consumables**: Quick-use healing potions, scrolls, and ammo.
   - Distinct visual pips for **Action**, **Bonus Action**, and **Reaction** that dynamically illuminate or dim as resources are expended during the turn.
2. **Dynamic Top Initiative Ribbon**:
   - A horizontal portrait carousel across the top of the arena displaying combat turn order.
   - The active combatant is prominently framed in glowing antique gold (`#c5a059`) with an initiative turn indicator.
   - Each portrait card shows a health gauge bar, Armor Class shield, and clickable condition chips.
   - Smooth slide animation when turns advance (`handleNextTurn`).
3. **Collapsible / Floating Combat Chronicle**:
   - Replaces the rigid left column with a collapsible side drawer or translucent chat-style HUD log in the bottom-left corner.
   - Live event filters: *All Events*, *Attacks & Spells*, *Damage & Healing*, *Condition Riders*.
   - Auto-scrolls on new actions with clean one-line summaries and expandable dice breakdowns.
4. **Focused Battlefield & Target Reticle**:
   - Central arena area dedicated to the active clash: selected enemy/hero vitals, vulnerabilities, resistances, and immediate visual range feedback.
   - Animated floating combat text (hits, criticals, misses, healing numbers).
5. **Fluid Responsive Widescreen & Mobile Viewport**:
   - Built to fit 100% viewport height (`100dvh`) without pushing outer document scrollbars or obscuring interactive controls.

---

## Pillar 10: 🎲 5e Mechanical Correctness & Rules Engine [IN PROGRESS]

### 10.1 The Problem: Data Without Enforcement

The bestiary and spell library contain comprehensive 5e data — spell ranges, damage types, enemy resistances/immunities/vulnerabilities, condition immunities, and action reach/range values — but the **combat execution engine treats all actions as generic damage pipes**. It never queries this data at resolution time, producing mechanically incorrect outcomes:

| Incorrect Behavior | Root Cause |
|---|---|
| Touch spells (Cure Wounds, Shocking Grasp) cast from 60 ft away | `cast_spell()` has no range validation |
| Fire Bolt deals full damage to a Fire Elemental (immune to fire) | `take_damage()` doesn't check `EnemyResistance` |
| Hold Person paralyzes an Undead (immune to paralyzed) | `auto_apply_condition_from_spell()` doesn't check `EnemyConditionImmunity` |
| Skeleton takes normal bludgeoning damage (should be vulnerable = 2×) | `take_damage()` only checks Barbarian Rage, not `EnemyResistance` or `CharacterResistance` |
| Enemy melee attack hits from 30 ft away | Combat AI doesn't enforce `EnemyAction.reach_or_range` |
| Spells don't propagate damage types to `take_damage()` | `cast_spell()` never looks up `SpellDamage.damage_type` |

### 10.2 Architecture: Validation Middleware Layer

Rather than editing 300+ individual spells, we build **validation and resolution middleware** that sits between "player clicks Cast/Attack" and "damage is applied". The middleware reads **existing populated data models** and enforces rules automatically.

```
                    ┌─────────────────────────────┐
                    │  Player / AI Action Request  │
                    │  (cast_spell, attack, etc.)  │
                    └──────────┬──────────────────┘
                               │
                    ┌──────────▼──────────────────┐
                    │  Phase 2: Spell Range Gate   │
                    │  Spell.range → Touch/Self/Xft│
                    │  Reject if out of range      │
                    └──────────┬──────────────────┘
                               │
                    ┌──────────▼──────────────────┐
                    │  Phase 1b: Damage Type       │
                    │  Lookup SpellDamage.type     │
                    │  Propagate to take_damage()  │
                    └──────────┬──────────────────┘
                               │
                    ┌──────────▼──────────────────┐
                    │  Phase 1a: Resistance Engine │
                    │  EnemyResistance /           │
                    │  CharacterResistance check   │
                    │  Apply: immune/resist/vuln   │
                    └──────────┬──────────────────┘
                               │
                    ┌──────────▼──────────────────┐
                    │  Phase 3: Condition Immunity │
                    │  EnemyConditionImmunity gate │
                    │  Block immune conditions     │
                    └──────────┬──────────────────┘
                               │
                    ┌──────────▼──────────────────┐
                    │  Damage Applied / Condition  │
                    │  Logged / Response Returned  │
                    └─────────────────────────────┘
```

### 10.3 Phase 1: Damage Type Propagation & Resistance Engine
**Impact: HIGH | Effort: MEDIUM | Risk: LOW**

The highest-value fix — affects every single combat damage interaction.

#### 10.3.1 Upgrade `CombatParticipant.take_damage()` (Phase 1a)

Currently `take_damage()` only checks Barbarian Rage resistance. Extend it to query:
- `EnemyResistance` model (for enemy targets) — resistance, immunity, or vulnerability by damage type.
- `CharacterResistance` model (for PC targets) — racial/class/item resistances.

The existing `apply_resistance()` utility in `combat/utils.py` already handles the math (`immunity → 0`, `resistance → half`, `vulnerability → 2×`). We just need to **call it** with the correct lookup.

Return value extended to include `resistance_info` so the combat log and frontend can display "RESISTED!" or "IMMUNE!" or "VULNERABLE!" floating text.

#### 10.3.2 Propagate Damage Type Through `cast_spell()` (Phase 1b)

Currently `cast_spell()` calls `t.take_damage(t_damage)` without a `damage_type` argument. The `Spell` model's `SpellDamage` relation already has `damage_type` FK populated from Open5e imports. Look it up and pass it through:

```python
# In cast_spell(), resolve damage type from spell library
spell_obj = Spell.objects.filter(name__iexact=spell_name).first()
spell_damage_type = None
if spell_obj:
    spell_dmg = spell_obj.damage_progression.first()
    if spell_dmg and spell_dmg.damage_type:
        spell_damage_type = spell_dmg.damage_type

# Pass through to damage resolution
t.take_damage(t_damage, damage_type=spell_damage_type)
```

Also applies to `combat_ai.py` enemy spell resolution paths.

### 10.4 Phase 2: Spell Range Validation
**Impact: HIGH | Effort: LOW | Risk: LOW**

Weapon attack range checking is already fully implemented (lines 354–397 of `combat_action_views.py` — melee reach, normal/long range, disadvantage at long range). We replicate this proven pattern for spells using the existing `Spell.range` field:

| `Spell.range` Value | Validation Rule |
|---|---|
| `"Self"` | Target must be caster themselves |
| `"Touch"` | Target must be within melee reach (5 ft, or 10 ft with reach weapons) |
| `"30 feet"`, `"60 feet"`, `"120 feet"` | Parse integer, check `caster.get_distance_to(target) <= max_range` |
| `"Sight"`, `"Unlimited"` | No distance restriction |

The `CharacterSpell` model links to `Spell` via FK (`spell` field), so range data is directly accessible. For enemy spellcasters, look up by name match.

### 10.5 Phase 3: Condition Immunity Enforcement
**Impact: MEDIUM | Effort: LOW | Risk: LOW**

Before applying any condition from spells or enemy ability riders, check `EnemyConditionImmunity`:

```python
# New guard in condition_effects.py
def is_condition_immune(participant, condition_name):
    if participant.encounter_enemy:
        return participant.encounter_enemy.enemy.condition_immunities.filter(
            condition__name=condition_name
        ).exists()
    return False
```

Integrated into:
1. `auto_apply_condition_from_spell()` — spell-based condition application.
2. `attack()` condition rider logic — enemy action hit riders (Wolf bite → prone, Poisonous Bite → poisoned).
3. `combat_ai.py` special action condition application.

When immunity blocks a condition, the combat log records: *"[Target] is immune to [Condition]!"* and frontend shows immunity floating text.

### 10.6 Phase 4: Enemy Action Range Enforcement
**Impact: MEDIUM | Effort: LOW | Risk: LOW**

`EnemyAction.reach_or_range` is already populated (e.g. `"5 ft."`, `"60/120 ft."`, `"15 ft. cone"`). The combat AI in `combat_ai.py` should validate this before executing attacks:

- **Melee actions** (`"5 ft."`, `"10 ft."`): Validate target is within reach. If not, prioritize movement toward target before attacking.
- **Ranged actions** (`"60/120 ft."`): Parse normal/long range. Apply disadvantage at long range.
- **AoE shapes** (`"15 ft. cone"`, `"30 ft. sphere"`): Already partially handled by the AoE system; ensure AI respects origin point distance.

### 10.7 Phase 5: Spell-Specific Rules Lookup Table (Incremental)
**Impact: MEDIUM | Effort: HIGH (ongoing) | Risk: MEDIUM**

For spell behaviors that can't be solved systemically (unique mechanics, special interactions), a **lookup table** in a dedicated `combat/spell_rules.py` module provides per-spell overrides:

```python
SPELL_RULES = {
    'cure wounds': {'range_override': 'touch', 'is_healing': True, 'no_undead_healing': True},
    'inflict wounds': {'range_override': 'touch', 'requires_attack_roll': True},
    'shocking grasp': {'range_override': 'touch', 'prevents_reactions': True},
    'shield': {'is_reaction': True, 'ac_bonus': 5, 'duration': 'until_start_of_next_turn'},
    # ... built incrementally, focusing on high-frequency spells first
}
```

**Priority tiers for spell-specific fixes:**
1. **Cantrips** (used every turn): Fire Bolt, Eldritch Blast, Sacred Flame, Shocking Grasp, Toll the Dead.
2. **Common combat spells**: Shield, Cure Wounds, Inflict Wounds, Guiding Bolt, Healing Word, Spiritual Weapon.
3. **AoE spells**: Fireball, Thunderwave, Burning Hands, Shatter (partially handled).
4. **Control spells**: Hold Person, Entangle, Web, Sleep, Command.
5. **Niche spells**: Everything else — fixed as encountered during play.

### 10.8 Priority Matrix & Implementation Order

```
                    HIGH IMPACT
                        │
    Phase 1             │            Phase 2
    (Resistances)       │            (Spell Range)
    ────────────────────┼────────────────────────
                        │
    Phase 5             │            Phase 3
    (Spell-Specific)    │            (Condition Immunity)
                        │            Phase 4
                        │            (Enemy Range)
                        │
                    LOW IMPACT
    HIGH EFFORT ────────┼──────── LOW EFFORT
```

| Order | Phase | Est. Time | Files Changed |
|---|---|---|---|
| 1st | Phase 1a: `take_damage()` resistance engine | ~30 min | `combat/models.py` |
| 2nd | Phase 1b: Spell damage type propagation | ~20 min | `combat/views/combat_action_views.py`, `combat/combat_ai.py` |
| 3rd | Phase 3: Condition immunity checking | ~15 min | `combat/condition_effects.py`, `combat/views/combat_action_views.py` |
| 4th | Phase 2: Spell range validation | ~30 min | `combat/views/combat_action_views.py` |
| 5th | Phase 4: Enemy action range enforcement | ~15 min | `combat/combat_ai.py` |
| 6th | Phase 5: Spell-specific rules (incremental) | Ongoing | New `combat/spell_rules.py` |

> **Design Principle**: Phases 1–4 are **systemic middleware fixes** that each improve hundreds of interactions at once with minimal code changes. Phase 5 is the long tail that we chip away at incrementally, prioritizing spells by usage frequency.

### 10.9 Scope Boundaries (Deferred to Future Work)

The following are intentionally **not** in scope for Pillar 10:
- Persistent spell effects & zones (Wall of Fire, Moonbeam repositioning)
- Counter-spell / Dispel Magic interaction chains
- Multi-class spell slot pooling rules
- Lair actions and regional effects
- Complex summon mechanics (Conjure Animals, Find Familiar)

These require deeper architectural patterns and are deferred until the foundation from Phases 1–5 is solid.

---

## Pillar 11: 🗺️ 2.5D Isometric Combat Grid, Thematic Battlemats & Multi-Tile Tokens [PLANNED]

### 11.1 The Problem: Flat 2D Matrix & Collapsed Multi-Tile Scale
While the interactive tactical grid (`BattleGrid.tsx`) successfully supports point-to-point movement, distance math, and AoE templates, it suffers from significant visual and spatial limitations:
1. **Collapsed Multi-Tile Scale**: Prior to fix, all creatures (from Tiny imps to Gargantuan dragons) visually occupied a single 1×1 tile (`w-9.5 h-9.5`), breaking the tabletop illusion of towering bosses and multi-creature board control.
2. **Flat Programmatic Grid Surface**: The arena renders as a stark flat obsidian matrix (`#090b10`) with dark border lines and emoji icons for pillars/barricades, lacking atmospheric depth, realistic stone masonry, or fantasy terrain textures.
3. **Flat Top-Down Perspective**: Looking straight down from 90° eliminates verticality, character silhouette visibility, and grounded token presence. Modern tactical RPGs (such as *Baldur's Gate 3*, *Solasta*, *Divinity*, *Final Fantasy Tactics*, and *Owlbear Rodeo 2.5D*) use angled perspective (45°–60°) with depth Z-sorting to make battlefields feel alive.
4. **Emoji Tokens vs. Physical Miniature Standees**: Creatures are represented by single emoji symbols (`🐉`, `👹`, `🛡️`) rather than high-definition circular tabletop miniatures, class crests, and monster portraits with beveled metallic bases.

---

### 11.2 2.5D Angled Viewport & Perspective Camera Architecture

```
                  ┌──────────────────────────────────────────────┐
                  │          2.5D Perspective Viewport           │
                  │   perspective: 1200px; transform-style: 3D   │
                  └──────────────────────┬───────────────────────┘
                                         │
                 ┌───────────────────────▼────────────────────────┐
                 │       Angled Tactical Grid Stage (Ground)      │
                 │     transform: rotateX(45deg) rotateZ(0deg)    │
                 │      • High-Res Thematic Battlemat Tilemap     │
                 │      • Dynamic Projected Range & AoE Reticles  │
                 │      • Realistic Grid Lines (subtle gold/dim)  │
                 └───────────────────────┬────────────────────────┘
                                         │
        ┌────────────────────────────────┴────────────────────────────────┐
        ▼                                                                 ▼
┌───────────────────────────────┐               ┌─────────────────────────────────┐
│     Multi-Tile Token Footprint │               │     Upright Billboard Standees  │
│ • Medium: 1×1 tile (5×5 ft)   │               │ • Counter-rotated rotateX(-45°) │
│ • Large: 2×2 tiles (10×10 ft) │               │ • Faces player camera directly  │
│ • Huge: 3×3 tiles (15×15 ft)  │               │ • Metallic circular base ring   │
│ • Gargantuan: 4×4+ (20×20 ft) │               │ • Authentic creature art/crest  │
│ • Dynamic oval ground shadow  │               │ • Dynamic Z-index: row * 10     │
└───────────────────────────────┘               └─────────────────────────────────┘
```

#### 11.2.1 Camera View Modes & Perspective Toggle
- **2.5D Tactical Angled View (Default)**:
  - Container uses CSS 3D context (`perspective: 1200px`, `perspective-origin: 50% 65%`).
  - Ground plane is tilted back at $45^\circ$ (`transform: rotateX(45deg)`), creating realistic foreground-to-background spatial recession.
- **Top-Down 2D Blueprint View (Toggle)**:
  - Instant 1-click toggle button on the grid controls (`[ 📐 2.5D Tactical ]` $\leftrightarrow$ `[ 🗺️ Top-Down 2D ]`) for players who prefer classic top-down tactical surveying.
- **Pan & Zoom Canvas**:
  - Full mouse wheel zoom ($0.75\times$ to $1.6\times$) and middle-click / drag pan with clamping within arena boundary walls.

#### 11.2.2 Y-Depth Z-Index Sorting
In an angled 2.5D perspective, objects standing on lower rows (closer to the camera) must render in front of objects standing on higher rows (further up).
- **Z-Index Formula**:
  $$\text{zIndex} = (\text{row} \times 10) + (\text{isFlying} \ ? \ 50 : 0) + (\text{isSelected} \ ? \ 100 : 0)$$
- Guarantees seamless depth occlusion where a standing warrior correctly overlaps a dragon behind them without clipping artifacts.

---

### 11.3 Authentic 5e Multi-Tile Footprint Scaling

Each creature's footprint on the grid maps to its canonical 5e size category:

| Size Category | 5e Space (Feet) | Grid Squares | Base Diameter | Visual Footprint & Miniature Ring Style |
| :--- | :--- | :--- | :--- | :--- |
| **Tiny** | 2.5 × 2.5 ft. | 0.5 × 0.5 (or centered 1×1) | 24px | Diminutive base with glowing aura pip (Familiars, Imps, Pixies) |
| **Small** | 5 × 5 ft. | 1 × 1 tile | 44px | Standard silver/bronze ring base (Halflings, Gnomes, Goblins) |
| **Medium** | 5 × 5 ft. | 1 × 1 tile | 48px | Standard gold-trimmed miniature base (Humans, Elves, Orcs) |
| **Large** | 10 × 10 ft. | 2 × 2 tiles | 96px | Heavy 2-tile wide base with radial ground shadow (Ogres, Horses, Minotaurs) |
| **Huge** | 15 × 15 ft. | 3 × 3 tiles | 144px | Massive 3-tile wide base with ambient footprint ring (Young/Adult Dragons, Giants) |
| **Gargantuan**| 20 × 20+ ft.| 4 × 4+ tiles | 192px+ | Colossal multi-tile stage presence with boss pulse aura (Ancient Dragons, Krakens) |

#### 11.3.1 Multi-Tile Spatial Mechanics
1. **Occupied Cell Matrix**:
   - When a Large ($2\times 2$) or Huge ($3\times 3$) unit occupies `(col, row)`, all $N \times N$ tiles `[col .. col+N-1, row .. row+N-1]` are registered in the obstacle collision map.
2. **Chebyshev Bounding-Box Distance**:
   - Melee reach and ranged distances calculate from the closest edge of the multi-tile bounding box:
     $$\text{dist} = \max(0, \Delta x_{\text{box}}, \Delta y_{\text{box}}, \Delta z_{\text{alt}})$$
3. **Reach Threat Perimeters**:
   - Threat aura circles visually project outward from the creature's entire multi-tile footprint (e.g., Huge dragon with 10 ft. reach threatens all cells within 2 tiles of any part of its $3\times 3$ body).

---

### 11.4 Realistic Physical Miniature Tokens (Billboard Standee Style)

Rather than flat digital stickers, tokens are styled after high-end physical tabletop miniatures and acrylic standees:

1. **Upright Billboard Counter-Rotation**:
   - While the ground plane tilts at $45^\circ$, each token's portrait disc counter-rotates (`transform: rotateX(-45deg)`).
   - This ensures character and monster art stands completely upright and directly faces the player's view, creating a tactile diorama feel.
2. **Weighted Circular Miniature Base**:
   - Grounded elliptical base ring with beveled rim, drop shadow, and faction tint:
     - 🛡️ **Player Adventurers**: Polished antique gold rim (`#c5a059`) with inner emerald health arc.
     - 👹 **Hostile Adversaries**: Crimson iron rim (`#ef4444`) with blood-red danger pulse.
     - 👑 **Bosses / Legendary Creatures**: Heavy double-banded filigree rim with pulsing runic light.
3. **Airborne Elevation Riser & Ground Shadow**:
   - Airborne creatures (`altitude > 0`):
     - The upright miniature token translates vertically along the Y-axis:
       $$\Delta y = -\text{Math.min}(48, 8 + \text{altitude} \times 1.2)\text{ px}$$
     - A translucent acrylic elevation rod connects the floating miniature to the ground.
     - A dark, diffuse oval ground shadow remains anchored to the terrain tiles directly below.
4. **Status & Aura Rings**:
   - **Concentration Aura**: Soft violet runic ring rotating beneath the caster's base.
   - **Condition Pips**: Miniature status badges (Stunned ⚡, Blinded 👁️, Poisoned 🧪) orbiting the upper lip of the base.

---

### 11.5 Thematic High-Resolution Battlemats & Environmental Biomes

Replaces the generic flat black grid with curated, high-atmosphere fantasy battlemats:

1. **Biome Battlemat Presets**:
   - 🏛️ **The Forgotten Crypt**: Cobblestone flagstones, carved burial slabs, dust particles, faint teal soul-lantern illumination.
   - 🌋 **Infernal Caldera**: Cracked black basalt slabs bordered by animated glowing magma channels with heat shimmer.
   - 🌲 **Verdant Wilderness / Dark Woods**: Tangled roots, pine needles, mossy boulders, fallen logs, dappled canopy light.
   - 🏰 **Gladiator Arena / Colosseum**: Scorched sand, trampled bloodstains, timber barricades, iron grate storm drains.
   - 🌊 **Sunken Mire / Flooded Ruins**: Submerged stone walkways, murky water reflections, dripping stalactites.
2. **Subtle Tactile Grid Overlay**:
   - High-precision 5-ft. grid lines rendered with fine gold/slate filigree (`opacity: 0.18–0.25`), perfectly aligned with multi-tile coordinates.
   - Dynamic cell coordinate markers (A1–J8) subtly etched into border stones.
3. **Dynamic Interactive Terrain Objects**:
   - Solid pillars and walls rendered as 2.5D extruded columns casting shadows across the floor.
   - Half-cover barricades (crates, low walls) that combatants can crouch behind.

---

### 11.6 Vertical Depth & Multi-Tier Battlemats (Topological Elevation, Cliffs & Fall Mechanics)

Tabletop combat is profoundly enhanced when terrain possesses **verticality** — balconies, cliffs, ramparts, sunken chasms, and bridges that dictate tactical advantage and danger.

```
                          [TOWER BALCONY / RAMPART: Z = +10 to +20 ft]
                                ┌───────────────────────────┐
                                │ 🏹 Ranger (High Ground)   │ • +2 To-Hit Bonus / Advantage
                                └─────────────┬─────────────┘ • Can fire over low cover
                                              │
                    [STONE STAIRCASE / RAMP]  │ 10 ft Drop (1d6 Fall Dmg + Prone)
                          ┌───────────────────┘
                          ▼
        ┌───────────────────────────────────┐
        │ 🛡️ MAIN ARENA FLOOR: Z = 0 ft     │
        │ • Melee Clash (Paladin vs Ogre)   │
        └─────────────────┬─────────────────┘
                          │ 
                          │ Cliff Edge / Shove Hazard (Thunderwave / Repelling Blast)
                          ▼
        ┌───────────────────────────────────┐
        │ ☠️ SUNKEN CHASM / PIT: Z = -10 ft │ • Toxic Gas / Spikes / Lava Hazard
        └───────────────────────────────────┘ • Difficult terrain to climb out
```

#### 11.6.1 Topological Elevation Tiers ($Z$-Coordinates)
Every cell $(x, y)$ in a battlemat layout possesses an intrinsic terrain elevation $Z$ in feet:
- **Sunken Chasms / Trenches ($Z = -10\text{ ft}$)**: Pits, acid canals, spike traps, or rushing underground rivers.
- **Main Arena Floor ($Z = 0\text{ ft}$)**: Standard ground combat plane.
- **Elevated Terraces / Dais ($Z = +5\text{ to }+10\text{ ft}$)**: Temple altars, ruined fortress ramparts, wooden scaffolding, stone bridges.
- **Watchtowers & High Perches ($Z = +15\text{ to }+20\text{ ft}$)**: Sniper nests, battlements, parapets.

#### 11.6.2 Visual 2.5D Layering & Iso-Extrusion
1. **Extruded 2.5D Cliff Faces**:
   - Elevated tiers are rendered with vertical rock faces and stone masonry blocks connecting the raised surface to the lower floor.
   - Raised cliffs cast soft ambient occlusion and directional drop-shadows onto lower tiles.
2. **Staircases, Ladders & Ramps**:
   - Explicit transition cells marked with directional steps that permit walking between $Z$-tiers without expending extra climbing movement.
3. **Multi-Level Masking & Overpasses**:
   - Arched stone bridges and catwalks allow creatures to stand **on top** ($Z = +10\text{ ft}$) while other units walk **underneath** ($Z = 0\text{ ft}$).
   - Units standing beneath higher architecture render with subtle transparency / occlusion outlines when camera angles overlap.

#### 11.6.3 5E Tactical Rules for Verticality
1. **High-Ground Tactical Advantage**:
   - Ranged weapon and spell attacks originating from $\ge 10\text{ ft.}$ elevation above the target receive a **+2 tactical to-hit bonus** (or Advantage on roll prediction) and bypass intervening half-cover.
2. **Falling Damage & Shoving Off Ledges**:
   - When a unit is shoved, pushed (*Thunderwave*, *Repelling Blast*), or steps off a cliff ledge:
     - **Damage**: $1\text{d}6$ bludgeoning damage per $10\text{ ft.}$ of vertical drop (max $20\text{d}6$).
     - **Prone Condition**: The fallen creature lands **Prone** unless it negates the damage (e.g. *Feather Fall*, Monk *Slow Fall*, or landing in deep water).
3. **Climbing & Jumping Movement Cost**:
   - Ascending a vertical wall without stairs or ladders costs **$2\times$ movement** ($10\text{ ft.}$ of movement budget per $5\text{ ft.}$ climbed), unless the creature has an innate Climb speed (e.g., Giant Spider).
   - Sheer or slick walls trigger an Athletics check (DC 12–15); failure halts movement or causes a slide.
   - Horizontal chasm jumps require $1\text{ ft.}$ of movement per foot cleared (up to Strength score with a 10-ft. running start).

---

### 11.7 Implementation Phases & Milestones

| Phase | Milestone | Deliverables | Status |
| :--- | :--- | :--- | :--- |
| **Phase 11.1** | **Multi-Tile Footprint Sizing Fix** | Fix `getParticipantSizeTiles` to parse `size_dimensions` dict, single-letter codes (`H`, `L`, `G`), and `size_display`. Update `cellOccupancy` multi-cell loops. | **`✅ COMPLETED`** |
| **Phase 11.2** | **2.5D Perspective Camera & Depth Sorting** | CSS 3D perspective viewport (`perspective: 1200px`, `rotateX(36deg)`), 2.5D/2D toggle button, tactical zoom controls (70%–150%), upright billboard counter-rotation (`rotateX(-36deg)`), dynamic Y-depth Z-index sorting. | **`✅ COMPLETED`** |
| **Phase 11.3** | **Upright Billboard Miniature Tokens & 3D BattleProps** | HeroForge 12-class miniature token suite, `tokenResolver.ts`, `BattleToken.tsx` (2.5D standees, weighted 3D beveled bases, HP radial gauge, threat badges, ground shadows, flight altitude acrylic riser stands), `BattleProp.tsx` (upright solid structures, stone plinths, cover badges), and beveled chiseled flagstone tiles. | **`✅ COMPLETED`** |
| **Phase 11.4** | **Thematic Battlemats & Atmospheric Shaders** | 5 high-res biome battlemats (Crypt, Magma, Woods, Colosseum, Mire), textured tilemaps, dynamic grid lines. | **`⏳ PLANNED`** |
| **Phase 11.5** | **Vertical Depth & Multi-Tier Elevation** | Multi-level $Z$-coordinate battlemats, extruded cliff faces, stairs/ramps, high-ground +2 bonus, fall damage & ledge shoving. | **`⏳ PLANNED`** |
| **Phase 11.6** | **Multi-Tile Movement & Squeezing Engine** | Multi-tile path clearance validation in pathfinding, 5e Squeezing rules, collision avoidance with tight corridors. | **`⏳ PLANNED`** |

---

## 12. Long-Term Phased Implementation Roadmap

```
Phase 0: Database & Infrastructure Foundation [COMPLETED]
├── PostgreSQL 16 Neon Cloud Serverless environment (Frankfurt eu-central-1)
├── Dual-branch strategy (dev branch for local, production branch for Render)
├── Dynamic database URL & connection pooling setup (dj-database-url)
├── High-speed bulk data migration (28,753 records migrated from SQLite to Neon)
├── All 67 PostgreSQL auto-increment sequences resynced
├── Full automated test suite verified (420/420 unit tests passing)
└── In-memory caching configuration (Django LocMemCache)

Phase 1: Security & Account Foundation [COMPLETED]
├── HttpOnly Cookie Refresh Token (Option A) with zero-JS exposure & XSS immunity
├── 15-Minute Access Token Lifespans & Automatic Axios Interceptor Renewal
├── SimpleJWT Refresh Token Rotation & Database Blacklisting (token_blacklist)
├── Password Reset Flow (anti-enumeration, 15-min timeout, complete session revocation)
├── Scoped Rate Limiting (5 attempts/min on login & password-reset)
├── 10/10 Automated Security Unit Tests Passing (430 total backend tests)
└── Redesigned Next.js Auth Suite (/login, /register, /forgot-password, /reset-password)

Phase 1.5: Frontend Layout & Decorative Aesthetic Overhaul [COMPLETED]
├── 1.5.1: App Shell, Dashboard & Characters Core [COMPLETED]
│   ├── Google Fonts Typography System (Cinzel Decorative, Lora, Fira Sans)
│   ├── Dark-Fantasy Color Palette (#0c0d12 canvas, #181a21 cards, #c5a059 gold, #d1cdb8 text, #a63a3a crimson)
│   ├── Universal App Shell with persistent Footer (Wizards SRD 5.1/5.2 attribution in #404552)
│   ├── Universal Navbar with 5E Dashboard logo, subpage actions, and user account dropdown
│   ├── Interactive 5E Dashboard with 3 Pillars & Option A Tooltips (hover slide/fade & mobile touch toggle)
│   ├── Dynamic Changelog card with real v1.8.0 updates & overhauled Chronicles history page
│   ├── 2-Column Responsive Characters Page matching mockup with FantasyCard frames & emerald HP stats
│   └── Overhauled Quick Random Roll preview & confirm modal styled to the fantasy aesthetic
├── 1.5.2: Decorative Embellishments, Class Heraldry & Parchment Scroll [COMPLETED]
│   ├── Ornamental golden filigree, refined corner brackets & subtle parchment/vignette textures for cards
│   ├── Class & race heraldic crests/icons for character cards (Paladin, Wizard, Rogue, Barbarian, etc.)
│   ├── Custom Three Pillars SVG icons in antique gold #c5a059 (Robed Adventurer, Swords Emblem, Crowned Skull)
│   ├── Dashboard & Characters page refinements (spacing, button styles, card proportions, micro-animations)
│   ├── Dual-Tome Lower Grid (Option B): Symmetrical 2-column layout beside Changelog
│   └── ParchmentScroll component with wooden dowels, brass finials, dark vellum texture, and wax seal stamp
├── 1.5.3: Combat Simulator & Encounter Setup Overhaul (/combat, /combat/[id]/setup, /combat/[id]) [COMPLETED]
│   ├── Modernize Combat Sessions list with dark obsidian #0c0d12, slate #181a21, and gold #c5a059 styling
│   ├── Backend query optimization for CombatSession list to eliminate slow WiFi latency bottlenecks
│   ├── Elegant fantasy loading states ("Summoning the arena...") replacing plain text
│   ├── Unified character selection cards with Gauntlet layout in combat setup
│   └── Overhauled tactical encounter setup & live battle views matching the tabletop aesthetic
└── 1.5.4: Character Detail & Creation Wizard Overhaul (/characters/[id], /characters/create) [COMPLETED]
    ├── Interactive digital character sheet overhaul (paperdoll inventory, spells, stats, saving throws)
    ├── 5-step character creation wizard restyled with luxury dark-fantasy theme
    ├── Dynamic equipment selection step with full weapon grid & archetype-weighted randomization
    └── 2024 ruleset background ASI options and multi-attribute allocation support

Phase 2: Bestiary & Monster Abilities Import [COMPLETED]
├── Relational EnemyAction, EnemyActionDamage, EnemyMultiattack, and EnemyTrait models
├── High-precision regex parsing engine (bestiary/parsers/action_parser.py)
├── 2,321 SRD monsters parsed and migrated in Neon PostgreSQL (7,522 actions, 7,384 damages, 6,617 traits)
├── Start-of-turn d6 recharge rolls, breath weapon saving throws, and Pack Tactics advantage
└── Authentic D&D 5e MonsterStatblockModal.tsx with live recharge indicators

Phase 3: Gauntlet Mode v0.1 (Wave Survival) [COMPLETED]
├── Procedural Wave Escalation engine across Waves 1–10 + Endless Overtime (CR scaling by party level)
├── Inter-Wave Respite Phase (Breather, Arcane Surge, Supply Drop, Tactical Boons)
├── Dedicated /gauntlet staging lobby with hero selection (1–6), biome themes, and run preview
├── In-Arena GauntletArenaHud banner, RespiteModal, and Victory/Defeat modals
└── Zero-risk snapshot hero isolation (GauntletSnapshotHero) protecting player character sheets

Phase 4: Tactical Monster AI Tuning & Autonomous Turns [COMPLETED]
├── Behavioral archetypes implemented (Brute, Skirmisher, Pack Hunter, Tactical Caster)
├── Multi-factor target scoring (incapacitated auto-crit +50, concentration +35, kill shot +30, low AC +15)
├── Autonomous step-by-step turn execution in Gauntlet with readable pauses and damage flashes
└── Restricted player controls during enemy turns (omitted End Turn button and hidden test damage tab)

Phase 4.5: Combat Arena Layout & Ergonomic UX Redesign [COMPLETED]
├── Bottom Tactical Action Dock (Weapons, Spells with slot pips, Maneuvers, Consumables hotbar, Resource pips)
├── Top Dynamic Initiative Ribbon (horizontal portrait cards with HP bars, condition chips, End Turn/AI controls)
├── Central Battlefield Arena (Attacker vs Defender clash stage with 1-click quick-target switcher & floating alerts)
├── Draggable & floating combat log HUD pill expanding into full filterable event log
├── Slide-out Participant Inspector Drawer with ability scores, equipped items & monster statblock links
├── Class Heraldry & Monster Archetype crest portraits with integrated AC shield badges
├── Floating combat text splats (Bold red HIT, bone-white MISS, card impact shake)
└── 3.5-second enemy attack linger for enhanced pacing and battle readability

Phase 4.6: Dedicated Spellcasting Action Modal & 5e Mechanics [COMPLETED]
├── Dedicated dark fantasy SpellCastModal.tsx replacing legacy physical attack routing
├── Dynamic spell slot selector (Cantrip vs leveled slot pips with upcast damage calculation)
├── Target picker (Enemies vs Party Allies & Self, auto-defaulting to Self for healing spells)
├── Spell Save DC resolution & condition auto-application (Hold Person -> Paralyzed, Sleep -> Unconscious)
├── Healing spells support (Cure Wounds, Healing Word restoring target HP without self-overwrite conflicts)
├── Player spell slot deduction & exhaustion verification in combat_action_views.py
└── Floating spell combat text (💚 HEALED! +X HP, 🛡️ SAVED!, 💥 SAVE FAILED!, ⚡ PARALYZED!)

Phase 5: Tactical Battlemap, AoE Spells & Movement [COMPLETED]
├── 2D Interactive Grid Battlemap component (BattleGrid.tsx, pan/zoom, d-pad, token coordinates)
├── Movement economy, difficult terrain & opportunity attacks with inline warning indicators
├── Spatial AoE spell targeting overlay (Sphere, Cone, Line, Cube) with multi-target save resolution
├── Thrown and ranged weapons (Javelin, Shortbow, Dart) with 5E range brackets and auto-melee/ranged detection
├── Thunderwave 10ft push with boundary clamping and collision safeguards
└── Duel Focus melee auto-switch with turn-end and kill auto-reset back to grid

Phase 5.5: Unified Combat Canvas & Streamlined Action Drawers [COMPLETED]
├── 5.5.1: Permanent Tactical Canvas & Contextual Clash Card [COMPLETED]
│   ├── Permanent Battle Grid Canvas (no jarring full-screen swapping, BattleGrid is permanent central arena)
│   ├── Dual Combatant Portraits: active hero avatar + class crest vs target creature portrait + monster archetype
│   ├── Hover-Preview: Hovering enemy token or chip reveals Clash Card with AC, HP, conditions & roll prediction
│   ├── Click-to-Lock: Clicking an enemy selects target and locks Clash Card with golden 📌 indicator
│   └── Auto-Dismiss: Clash Card automatically hides after 600ms on enemy death, on target switch, or on turn advance
├── 5.5.2: 5E Action Economy Resource Pills [COMPLETED]
│   ├── Action Pill (⚔️ Action with attacks remaining count • dim line-through when spent)
│   ├── Bonus Action Pill (⚡ Bonus Action • amber when ready, dim line-through when spent)
│   ├── Movement Budget Pill (🦶 Move: X/Y ft progress tracker • cyan when ready)
│   ├── Reaction Pill (🛡️ Reaction • blue when ready, dim line-through when spent)
│   └── Roll Advantage / Inspiration Pill (⭐ Inspiration toggle, ADV/DISADV badges with tactical reasons)
└── 5.5.3: Streamlined Categorized Action Drawers [COMPLETED]
    ├── ⚔️ 1-Click Strike Action: Equipped primary weapon strike button right on dock (0 menus needed to attack)
    ├── 🗡️ Weapons Arsenal Drawer: Carried melee, off-hand, ranged, and thrown weapons with 5e range tags and attack buttons
    ├── 📖 Spellbook Drawer: Popover grid categorized by spell level (Cantrips, 1st, 2nd...) with slot counters, AoE Aim on Grid & Upcast
    ├── 🔱 Class Features & Feats Drawer: Barbarian Rage, Reckless Attack, Fighter Action Surge & Second Wind, Paladin Lay on Hands, Rogue Cunning Action, Character Feats (Sentinel, GWM, Sharpshooter, War Caster, etc.) & Class Traits
    ├── 🎒 Consumables Pouch Drawer: Recipient ally selector + Potion of Healing (Drink/Administer) + inventory potions & scrolls
    ├── 🏃 Universal Maneuvers Drawer: Dash, Disengage, Dodge, and Hide
    └── ⏩ Pinned End Turn Button: Permanently accessible on the right dock

Phase 5.6: 5e Mechanical Correctness & Rules Engine [COMPLETED]
├── Phase 1a: Damage resistance/immunity/vulnerability engine in take_damage() [COMPLETED]
│   └── Query EnemyResistance & CharacterResistance models by damage type at damage time with combat log annotations
├── Phase 1b: Spell damage type propagation from SpellDamage.damage_type into take_damage() [COMPLETED]
├── Phase 2: Spell range validation (Touch/Self/X ft) using Spell.range and fallback lookup [COMPLETED]
├── Phase 3: Condition immunity enforcement via EnemyConditionImmunity gate in spells, attacks, and AI [COMPLETED]
├── Phase 4: Enemy action reach/range enforcement in combat AI from EnemyAction.reach_or_range [COMPLETED]
└── Phase 5: Incremental spell-specific rules lookup table (combat/spell_rules.py) with undead healing guards & post-effects [COMPLETED]

Phase 5.7: Animated Battle Grid Token Overlays & Movement-First Tactical Monster AI (v1.13.0) [COMPLETED]
├── Dedicated CSS-interpolated token overlay layer on BattleGrid with 450ms coordinate transitions
├── Phased enemy turn execution in page.tsx (500ms slide delay -> 1200ms attack damage linger -> turn advance)
├── Grid-aware tactical target selection (Chebyshev distance, reachability scoring, +60 melee adjacent priority)
├── Movement-first Monster AI pipeline (melee closes into reach before attack, snipers maintain 15–60 ft distance)
├── Tactical repositioning for ranged snipers trapped in melee (<= 5 ft) to eliminate attack disadvantage
└── Multiattack sequence re-targeting when primary targets drop mid-turn

Phase 5.8: Canonical Monster Multiattack Routines & Spell Attack Cooldown Rotation (v1.14.0) [COMPLETED]
├── Multiattack Sequence Parser: Regex-based extraction of multi-weapon attack routines (e.g. Bear 1 Bite + 1 Claws)
├── Fallback Distinct Attack Rotation: Cycles across distinct candidate actions when attack count > 1
├── Canonical Bestiary Spell Detection: Extracts spells from statblock text matching SRD grimoire (e.g. Mage Fireball, Cone of Cold)
├── Cooldown & Tactical Anti-Spam: 2-round simulated internal cooldown for high-impact monster spells and special abilities
└── Autonomous Monster Action Verification: Automated tests for multiattack, recharge, and distinct attack rotation

Phase 5.9: Character Sheet Spell Slot Dashboard & Combat Action Dock Ergonomics [COMPLETED]
├── 5.9.1: Character Sheet Spell Slot Page & Grimoire Redesign [COMPLETED]
│   ├── Dedicated Spell Slot Overview Matrix: High-level dashboard banner tracking slots per level (1st-9th) at a glance
│   ├── Interactive Slot Dials / Pips: Visually prominent available vs. expended slot toggles with +/- quick adjusters
│   ├── Pact Magic vs. Spellcasting Separation: Clear visual distinction for Warlock short-rest slots vs standard long-rest slots
│   ├── Quick Rest Recovery Triggers: Direct Short Rest / Long Rest slot recovery buttons integrated inside the spells tab
│   ├── Spell Filtering & Organization: Filter by Prepared, Ritual, Casting Time (Action/Bonus Action/Reaction), and School
│   └── Spellcasting Attribute Crest: Sticky header showing Spell Save DC, Spell Attack Bonus, and Prepared limit status
├── 5.9.2: Combat View Bottom Toolbar & Action Dock Ergonomic Redesign [COMPLETED]
│   ├── Concise Ergonomic Button Layout: Compact height profile to minimize vertical occlusion of the battle grid
│   ├── Grouped Action Clusters: Clear visual clustering (Offensive: Strike/Arsenal/Spells | Utility: Feats/Consumables/Maneuvers | Turn: End Turn)
│   ├── Condensed Button Styling: Icon-first buttons with badge counters (e.g. ⚔️ Strike, 🗡️ Arsenal (3), 📖 Spells (4), ✨ Feats (2))
│   ├── Quick Keyboard Shortcuts: Tooltip hints and hotkeys (1-5 for drawers, Space for Strike, Enter for End Turn)
│   ├── Contextual Ready States: Dynamic visual dimming / glow badges showing available vs exhausted actions in each category
│   └── Mobile & Ultra-wide Viewport Scaling: Streamlined responsive wrapping preventing button overflow and vertical shifting
└── 5.9.3: Tactical Combat Spell Filter, Gauntlet Pruning & Buff Engine Verification [COMPLETED]
    ├── Combat vs. Utility Spell Classifier (spellClassification.ts): Classifies spells into combat-ready actions/reactions/buffs vs out-of-combat exploration/downtime spells
    ├── ActionDock Grimoire Filter Toggle: Seamless switch between [⚔️ Combat Spells (N)] and [📜 All Spells (N)] with out-of-combat badges (⏳ 1 min, 🕯️ Non-Combat RP)
    ├── Strict Gauntlet Mode Pruning: Automatically locks Grimoire to combat-only spells with dedicated gold indicator badge in Gauntlet survival runs
    ├── SpellCastModal Tactical Buff Banners: Green tactical buff badges with 5e mechanical preview for Shield, Bless, Mage Armor, Shield of Faith, Haste, Blur, etc.
    └── Automated Buff Mechanics Test Suite: Comprehensive test suite in combat/test_buff_mechanics.py verifying Shield (+5 AC), Bless (+1d4 attacks and saving throws), and Mage Armor (13 + Dex AC)


Phase 6: 2.5D Isometric Combat Grid & Environmental Arena System (Pillar 11) [PLANNED]
├── 6.1: Multi-Tile Creature Footprint Scaling (Large 2×2, Huge 3×3, Gargantuan 4×4) [COMPLETED]
├── 6.2: 2.5D Angled Viewport projection (45° perspective tilt with 2D/2.5D view toggle & Y-depth Z-sorting)
├── 6.3: Upright 2.5D Billboard Miniature Tokens (counter-rotated standees, circular metallic bases, airborne risers)
├── 6.4: Thematic Biome Battlemats (Crypt, Infernal Magma, Colosseum Sand, Sunken Mire, Dark Woods)
├── 6.5: Multi-Tile Pathfinding & 5e Squeezing Rules
├── 6.6: Line-of-Sight raycaster & Cover (+2 / +5 AC) modifiers
├── 6.7: Hazard zones (Lava, Acid, Spikes) & forced movement pushes
└── 6.8: Interactive destructible obstacles & 2.5D terrain props

Phase 7: Campaign Mode (Persistent Adventure & Leveling) [FUTURE]
├── Node-based Campaign Map (biomes, encounters, treasure, campsites)
├── 1-6 Party selection & persistence
├── Post-encounter XP distribution & Level-Up triggers
└── Interactive Level-Up Wizard UI (HP, Spells, Subclasses, ASI)
```

---

## 13. Master Reference Document Status

> [!NOTE]
> This artifact serves as the active **Master Plan** for all upcoming feature implementations and architectural decisions across the 5e Campaign Manager. All future iterations, issues, and PR-style increments will reference and build directly upon the schemas, rules, and roadmaps documented here.

