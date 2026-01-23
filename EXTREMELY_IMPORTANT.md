---
name: SRD Compliance & Legal Safety Checklist
about: Verify SRD / Open5e compliance before major features or releases
title: "[SRD] Compliance Checklist – "
labels: ["legal", "compliance", "release-blocker"]
assignees: []
---

## 🧠 Purpose
This issue ensures the project remains compliant with:
- D&D System Reference Document (SRD 5.x)
- Creative Commons Attribution (CC BY 4.0)
- Open5e licensing
- Wizards of the Coast IP restrictions

This checklist **must be completed before release**.

---

## 1️⃣ Data Ingestion (Open5e / SRD)

### Source Filtering
- [ ] Import **SRD-only** content
- [ ] Verify license metadata per endpoint
- [ ] Exclude non-SRD content:
  - [ ] Classes
  - [ ] Subclasses
  - [ ] Backgrounds
  - [ ] Feats
  - [ ] Spells
- [ ] Exclude protected monsters (e.g. Beholder, Mind Flayer)
- [ ] Exclude named NPCs
- [ ] Exclude named settings / planes

### Data Hygiene
- [ ] Store `source`, `license`, `is_srd` flags per record
- [ ] Log excluded content
- [ ] Version imported datasets (e.g. SRD 5.1 vs 5.2.1)

---

## 2️⃣ Rules Engine

- [ ] Mechanics implemented independently of content
- [ ] No hardcoded monster, class, or setting names
- [ ] No embedded flavor or lore text
- [ ] Rules engine operates purely on abstract data

---

## 3️⃣ Character Creation

### Allowed Options Only
- [ ] SRD races/species only
- [ ] SRD classes only
- [ ] SRD subclasses only
- [ ] SRD feats only
- [ ] SRD spells only

### Background Handling
- [ ] No PHB-only backgrounds included
- [ ] Custom background creator available
- [ ] All background features:
  - [ ] Original names
  - [ ] Original mechanics
  - [ ] Original text

### User Content
- [ ] User-created content clearly labeled
- [ ] Homebrew content isolated from core SRD data

---

## 4️⃣ Combat Simulation

- [ ] Uses SRD combat rules only
- [ ] Only SRD monsters included by default
- [ ] Reskinned or procedurally generated monsters are original
- [ ] User-imported monsters clearly marked

---

## 5️⃣ UI / UX Copy

### Allowed Language
- [ ] “SRD-based”
- [ ] “5e-compatible”
- [ ] “Fantasy RPG”

### Avoided Language
- [ ] No “D&D”
- [ ] No “Dungeon Master”
- [ ] No “Official”
- [ ] No Wizards of the Coast branding

### Terminology
- [ ] “GM” or “Narrator” instead of “DM”
- [ ] “Character” instead of “D&D character”

---

## 6️⃣ Branding & Naming

- [ ] App name avoids D&D trademarks
- [ ] No logos or symbols resembling Wizards IP
- [ ] Marketing copy avoids endorsement implications

---

## 7️⃣ Attribution (Required)

### SRD Attribution
- [ ] SRD attribution included
- [ ] Correct CC BY 4.0 wording
- [ ] Visible placement (footer / about / README)

### Open5e Attribution
- [ ] Open5e credited as data source
- [ ] License referenced if required

---

## 8️⃣ Disclaimers

- [ ] “Not affiliated with or endorsed by Wizards of the Coast” included
- [ ] Disclaimer written in plain language

---

## 9️⃣ Monetization (If Applicable)

### Allowed
- [ ] Tooling / automation features
- [ ] UX improvements
- [ ] Subscriptions or premium features

### Disallowed
- [ ] No paywalling raw SRD text
- [ ] No selling Wizards-owned content

---

## 🔟 Final Sanity Check

- [ ] No protected names remain in the database
- [ ] No trademarked terms appear in UI or marketing
- [ ] Attribution is present and correct
- [ ] A reasonable user would NOT think this is official D&D

---

## 🧾 Notes / Follow-ups
_Add anything that needs review, refactor, or future tracking._