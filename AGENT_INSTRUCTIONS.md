# Agent Instructions & 5E Project Testing Protocol

## 1. Operating Rules & Core Constraints
- **Strict SRD Compliance**: Only official SRD 5.1 and 2024 SRD 5.2 rules and mechanics are permitted. Closed-content commercial player options (e.g., PHB Battle Master, Eldritch Knight) must not be imported or simulated in this codebase.
- **Smallest Useful Increments**: Develop in small, verifiable slices. Never attempt massive multi-system rewrites in a single pass.
- **Regression Testing**: Every incremental modification must be verified with automated test suites before proceeding.
- **Protocol Rule: "Also Report What You Didn't Test"**: At the conclusion of every development session or audit update, always explicitly document what was *not* tested (e.g., live multiplayer websockets, uninstalled modules, end-to-end browser suites) to ensure transparency.

## 2. Testing Protocol
- Backend tests are executed via `py -3 manage.py test <test_label>`.
- Keep test suites isolated and fast.
- Maintain test coverage for class features, weapon masteries, metamagic, spell categories, and subclasses.

## 3. Class Passives & High-Level Mechanics Guidelines
- Follow standard 5e math and precedence:
  - Ability check modifiers: ability mod + proficiency (or half-proficiency for Remarkable Athlete) + situational bonus.
  - Reliable Talent (Rogue 11+): Any proficient d20 check roll of 1–9 is treated as 10.
  - Indomitable Might (Barbarian 18+): If total Strength check < Strength score, use Strength score.
  - Relentless Rage (Barbarian 11+): On dropping to 0 HP while raging, CON save DC 10 (scaling +5 per success) to drop to 1 HP instead.
  - Aura of Protection (Paladin 6+): All saving throws for Paladin and conscious allies within range (10 ft, 30 ft at level 18) gain +CHA modifier (minimum +1).
  - Aura of Courage (Paladin 10+): Paladin and conscious allies within range (10 ft, 30 ft at level 18) are immune to frightened condition.
