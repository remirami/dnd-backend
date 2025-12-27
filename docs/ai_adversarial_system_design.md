# AI Adversarial System for Campaign Gauntlet

## Overview

This document outlines an AI system that acts as an adversarial game master, making intelligent decisions that challenge players in the roguelike gauntlet campaign system. The AI analyzes player state, adapts encounter difficulty, manages enemy tactics, and creates dynamic challenges.

## Core Concept

Instead of static, pre-designed encounters, the AI dynamically:
- **Adapts encounters** based on player performance and resources
- **Makes tactical decisions** for enemies during combat
- **Manages encounter flow** and pacing
- **Adjusts difficulty** to maintain challenge without being unfair
- **Creates narrative tension** through strategic resource depletion

---

## 1. AI Roles & Responsibilities

### A. Encounter Design AI
**Purpose**: Generate and modify encounters based on player state

**Decisions it makes:**
- Which enemies to include in an encounter
- Number of enemies (scaling with party size/level)
- Enemy positioning and initial tactics
- Environmental hazards or terrain features
- Encounter difficulty rating

**Example Scenario:**
```
Player has: 3 characters, all at 80% HP, 2 short rests remaining, used 1 long rest
AI Decision:
- Medium difficulty encounter (not too easy, but manageable)
- Mix of melee and ranged enemies (tests positioning)
- Include 1 enemy with AoE to pressure resource use
- Total CR: ~4-5 (balanced for party)
```

### B. Combat Tactics AI
**Purpose**: Control enemy actions during combat with intelligent decision-making

**Decisions it makes:**
- Target selection (focus fire vs spread damage)
- Ability usage (when to use powerful abilities)
- Positioning (melee vs ranged, flanking)
- Resource management (save abilities for later rounds)
- Retreat/call reinforcements (if encounter allows)

**Example Tactics:**

**1. Focus Fire Strategy:**
```
Round 1: AI identifies weakest character (lowest HP/AC)
Round 2-3: All enemies focus on that character
Goal: Eliminate one party member quickly (reduce action economy)
```

**2. Resource Depletion:**
```
AI tracks party spell slots and hit dice
Encounters 1-2: Use AoE to force spell usage
Encounter 3: Lower damage, focus on HP depletion
Goal: Exhaust party resources before final encounter
```

**3. Adaptive Difficulty:**
```
Party doing well? → Spawn reinforcements or buff enemies
Party struggling? → Ease up (enemies make suboptimal choices)
Goal: Maintain challenge without TPK (unless intentional)
```

### C. Encounter Pacing AI
**Purpose**: Control the flow and difficulty curve of the gauntlet

**Decisions it makes:**
- When to insert easy vs hard encounters
- Rest opportunities (allow short rest? force long rest?)
- Encounter spacing (rush vs recovery)
- Final boss difficulty scaling

**Example Pacing:**
```
Encounter 1 (Easy): Warm-up, test basic abilities
Encounter 2 (Medium): Pressure resources slightly
Encounter 3 (Hard): Major resource drain
[Short Rest Opportunity]
Encounter 4 (Medium): Test recovery
Encounter 5 (Very Hard): Boss fight, all resources needed
```

---

## 2. AI Decision Making Systems

### A. State Analysis

The AI analyzes:
```python
PlayerState = {
    "party_size": int,
    "average_hp_percentage": float,  # 0.0-1.0
    "resources_remaining": {
        "hit_dice": int,
        "spell_slots": dict,  # {"1": 3, "2": 2, ...}
        "short_rests_used": int,
        "long_rests_used": int,
        "long_rests_remaining": int,
        "consumables": int,
    },
    "party_composition": {
        "tanks": int,      # High HP/AC
        "dps": int,        # High damage
        "support": int,    # Healing/buffs
        "spellcasters": int,
    },
    "threat_level": str,   # "weak", "healthy", "depleted", "critical"
    "encounters_completed": int,
    "encounters_remaining": int,
}
```

### B. Decision Trees

**1. Encounter Difficulty Selection:**
```
IF party.average_hp_percentage > 0.8 AND resources.hit_dice > 5:
    difficulty = "hard"
    pressure_resources = True
ELIF party.average_hp_percentage < 0.4:
    difficulty = "easy" OR "medium"
    allow_recovery = True
ELSE:
    difficulty = "medium"
```

**2. Enemy Selection:**
```
IF party.has_weak_save == "DEX":
    include_enemies_with_dex_saves = True
    
IF party.spellcasters > 0:
    include_spellcaster_enemies = True
    counter_spells = True
    
IF party.resources.spell_slots["3"] > 0:
    pressure_with_resistances = True
```

**3. Combat Tactics:**
```
ROUND 1: Assess party composition
  - Identify highest threat (healer? DPS?)
  - Identify weakest target (low AC? Low HP?)

ROUND 2+: Execute strategy
  - Focus fire on weakest OR highest threat?
  - Use AoE if 3+ party members grouped
  - Save legendary actions for critical moments
```

---

## 3. Implementation Examples

### Example 1: Adaptive Encounter Generation

```python
class AIEncounterDesigner:
    def generate_encounter(self, campaign_state):
        party = campaign_state.get_party_state()
        
        # Calculate target difficulty
        base_difficulty = self._calculate_difficulty(party)
        
        # Select enemy composition
        enemies = self._select_enemies(
            difficulty=base_difficulty,
            party_size=party.size,
            party_composition=party.composition,
            target_cr=party.average_level * 1.5
        )
        
        # Adjust encounter based on party resources
        if party.resources_remaining['spell_slots'] > 0:
            # Add enemies that counter spellcasters
            enemies.extend(self._get_anti_magic_enemies())
        
        if party.average_hp_percentage > 0.9:
            # Party too healthy, add pressure
            enemies.append(self._get_burst_damage_enemy())
        
        return Encounter(
            name=f"Encounter {campaign_state.encounter_number}",
            enemies=enemies,
            difficulty=self._adjust_for_pacing(campaign_state),
            ai_controlled=True
        )
```

### Example 2: Combat AI Tactics

```python
class AICombatController:
    def decide_action(self, enemy, combat_state):
        party = combat_state.party_members
        enemy_state = combat_state.get_enemy_state(enemy)
        
        # Analyze party state
        weakest = self._find_weakest_target(party)
        healer = self._find_healer(party)
        clustered = self._are_party_clustered(party)
        
        # Decision logic
        if clustered and enemy.has_aoe:
            return Action(
                type="aoe_attack",
                target=party.cluster_center,
                priority="high"
            )
        
        if healer and enemy.can_reach(healer):
            return Action(
                type="attack",
                target=healer,
                priority="critical",  # Eliminate healing
                reason="target_healer"
            )
        
        if weakest.hp_percentage < 0.3:
            return Action(
                type="attack",
                target=weakest,
                priority="high",
                reason="finish_off_weak_target"
            )
        
        # Default: attack most accessible target
        return Action(
            type="attack",
            target=self._get_most_accessible_target(party),
            priority="medium"
        )
```

### Example 3: Encounter Pacing AI

```python
class AIPacingController:
    def should_allow_rest(self, campaign_state):
        party = campaign_state.get_party_state()
        encounters_remaining = campaign_state.encounters_remaining
        
        # Too many resources? Don't allow rest yet
        if party.resources_remaining['hit_dice'] > party.size * 2:
            return False
        
        # Critical health? Allow short rest
        if party.average_hp_percentage < 0.3:
            return True
        
        # Near end of gauntlet? Limit rest opportunities
        if encounters_remaining <= 2:
            if campaign_state.rests_used < 1:
                return True  # One last rest before boss
            return False
        
        # Standard pacing: allow rest every 2-3 encounters
        if campaign_state.encounters_completed % 3 == 0:
            return True
        
        return False
    
    def calculate_next_difficulty(self, campaign_state):
        party = campaign_state.get_party_state()
        
        # Difficulty curve: Easy → Medium → Hard → Boss
        encounter_num = campaign_state.encounter_number
        
        if encounter_num == campaign_state.total_encounters:
            return "boss"  # Final encounter
        
        # Adjust based on party state
        if party.resources_remaining['long_rests'] > 0:
            return "hard"  # Pressure them to use rest
        else:
            return "medium"  # Can't rest anyway, be fair
```

---

## 4. AI Personality Types

Different AI "personalities" for varied gameplay:

### A. Merciless AI
- **Focus**: Eliminate party members quickly
- **Tactics**: Focus fire, prioritize healers, use abilities early
- **Difficulty**: Always on the harder side
- **Use Case**: Hardcore mode, experienced players

### B. Tactical AI
- **Focus**: Optimal strategy, resource management
- **Tactics**: Adapt to party composition, counter strategies
- **Difficulty**: Scales with player skill
- **Use Case**: Standard gameplay, balanced challenge

### C. Opportunistic AI
- **Focus**: Exploit weaknesses and mistakes
- **Tactics**: Punish clustering, target low saves, interrupt actions
- **Difficulty**: Variable (easy mistakes, hard perfect play)
- **Use Case**: Teaches positioning and tactics

### D. Narrative AI
- **Focus**: Create dramatic moments
- **Tactics**: Escalate tension, create "oh shit" moments
- **Difficulty**: Story-driven (easy → build → climax)
- **Use Case**: Thematic campaigns, cinematic feel

---

## 5. Technical Architecture

### A. AI Service Layer

```
campaigns/
├── ai/
│   ├── __init__.py
│   ├── encounter_designer.py      # Generates encounters
│   ├── combat_controller.py       # Controls enemy actions
│   ├── pacing_controller.py       # Manages difficulty curve
│   ├── state_analyzer.py          # Analyzes party state
│   ├── decision_engine.py         # Core decision logic
│   └── ai_personalities.py        # Different AI types
```

### B. Integration Points

**1. Campaign Start:**
```python
campaign.start(ai_enabled=True, ai_personality="tactical")
```

**2. Encounter Generation:**
```python
# Instead of pre-designed encounters
encounter = ai_designer.generate_encounter(campaign_state)
campaign.add_encounter(encounter)
```

**3. Combat Actions:**
```python
# During combat turn
if enemy.is_ai_controlled:
    action = ai_controller.decide_action(enemy, combat_state)
    combat.execute_action(enemy, action)
```

### C. Data Models

```python
class AIConfig(models.Model):
    """AI personality and behavior settings"""
    campaign = models.OneToOneField(Campaign, related_name='ai_config')
    personality = models.CharField(choices=[...])  # merciless, tactical, etc.
    difficulty_adjustment = models.FloatField(default=1.0)  # 0.5 to 2.0
    adaptive_difficulty = models.BooleanField(default=True)
    aggression_level = models.IntegerField(default=5)  # 1-10
    
class AIState(models.Model):
    """Tracks AI decisions and analysis"""
    campaign = models.ForeignKey(Campaign, related_name='ai_states')
    encounter = models.ForeignKey(CampaignEncounter)
    analysis = models.JSONField()  # Party state analysis
    decisions = models.JSONField()  # AI decisions made
    timestamp = models.DateTimeField(auto_now_add=True)
```

---

## 6. Example Game Flow

### Scenario: 3-Encounter Gauntlet

**Encounter 1 - AI Analysis:**
```
Party: 3 characters, all 100% HP, full resources
AI Decision: "Party is too strong, apply pressure"
Result: Medium-hard encounter with AoE enemies
Outcome: Party uses 2 spell slots, average HP drops to 70%
```

**Between Encounters:**
```
AI Analysis: "Party at 70% HP, 1/3 spell slots used"
AI Decision: "Allow short rest, but next encounter will be harder"
Result: Short rest available, party heals to 85%
```

**Encounter 2 - AI Adapts:**
```
AI Analysis: "Party recovered, but used a rest"
AI Decision: "Increase difficulty, target the healer"
Result: Hard encounter, enemies focus fire on cleric
Outcome: Cleric drops to 30% HP, party average at 60%
```

**Final Encounter:**
```
AI Analysis: "Party depleted (60% HP, few resources)"
AI Decision: "Boss fight - balanced but challenging"
Result: Custom boss encounter scaled to party state
Outcome: Close fight, party barely survives
```

---

## 7. Benefits of AI System

### A. Dynamic Gameplay
- Every run is different
- Encounters adapt to party composition
- No "solved" strategies

### B. Balanced Difficulty
- Prevents steamrolling
- Avoids unfair TPKs (if desired)
- Maintains tension throughout

### C. Educational
- Teaches tactics through experience
- Shows consequences of poor resource management
- Demonstrates optimal play patterns

### D. Replayability
- Same campaign, different challenges
- AI learns from player patterns (optional)
- Varied encounter compositions

---

## 8. Implementation Phases

### Phase 1: Basic AI (MVP)
- ✅ Encounter difficulty scaling
- ✅ Simple target selection (focus weakest)
- ✅ Resource tracking and basic adaptation

### Phase 2: Tactical AI
- ✅ Multi-enemy coordination
- ✅ Ability usage optimization
- ✅ Positioning awareness

### Phase 3: Advanced AI
- ✅ Personality system
- ✅ Learning from player patterns
- ✅ Dynamic encounter generation
- ✅ Narrative pacing

### Phase 4: Advanced Features
- ✅ Configurable AI difficulty
- ✅ Player vs AI modes
- ✅ AI tournament modes
- ✅ Replay analysis

---

## 9. Configuration Options

```python
AIConfig = {
    "enabled": True,
    "personality": "tactical",  # or "merciless", "opportunistic", "narrative"
    "difficulty": {
        "base_multiplier": 1.0,      # 0.5 (easy) to 2.0 (brutal)
        "adaptive": True,             # Adjust based on performance
        "min_difficulty": 0.7,       # Never easier than this
        "max_difficulty": 1.5,       # Never harder than this
    },
    "tactics": {
        "focus_fire": True,          # Concentrate damage
        "target_healers": True,      # Prioritize healers
        "use_aoe": True,             # Cluster punishment
        "save_abilities": True,      # Don't waste cooldowns
    },
    "pacing": {
        "allow_rests": True,         # Can grant rest opportunities
        "rest_frequency": "moderate", # "rare", "moderate", "generous"
        "escalation_rate": "medium",  # How quickly difficulty increases
    }
}
```

---

## 10. Challenges & Considerations

### A. Balance
- **Challenge**: AI too smart = unfair, AI too dumb = boring
- **Solution**: Configurable difficulty, personality system

### B. Predictability
- **Challenge**: Patterns become obvious
- **Solution**: Randomization, multiple personalities, learning

### C. Performance
- **Challenge**: AI calculations on every turn
- **Solution**: Cache analysis, batch decisions, async processing

### D. Player Agency
- **Challenge**: AI controlling everything feels scripted
- **Solution**: Player choices still matter, AI adapts to them

---

## 11. Future Enhancements

- **Machine Learning**: Train AI on successful vs failed runs
- **Player Preferences**: AI learns what challenges player enjoys
- **Co-op AI**: AI controls some party members in solo play
- **AI vs AI**: Watch AI parties battle (tournament mode)
- **Narrative AI**: Generate story elements based on encounters
- **Procedural Generation**: Fully dynamic campaigns

---

## Summary

The AI adversarial system transforms the campaign from static encounters into a dynamic, adaptive challenge that:
- Responds to player decisions
- Maintains appropriate difficulty
- Creates varied, interesting encounters
- Teaches tactical play through experience
- Provides high replayability

The system can start simple (basic target selection) and evolve into a sophisticated adaptive opponent that creates unique challenges every playthrough.

