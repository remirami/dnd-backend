# Frontend Implementation Plan

## 🎯 Overview

Build a modern, responsive frontend for the D&D 5e Roguelike Gauntlet Backend using React and TypeScript.

## 🛠️ Technology Stack Recommendation

### Core Framework
- **React 18+** with **TypeScript** - Type safety and modern React features
- **Vite** - Fast build tool and dev server
- **React Router v6** - Client-side routing

### State Management
- **TanStack Query (React Query)** - Server state management, caching, and API calls
- **Zustand** or **Context API** - Client state management (user session, UI state)

### UI Framework
- **Tailwind CSS** - Utility-first CSS framework
- **shadcn/ui** - High-quality, customizable React components
- **Framer Motion** - Animations and transitions

### API Integration
- **Axios** - HTTP client with interceptors for JWT tokens
- **TypeScript types** - Generated from backend models

### Additional Libraries
- **React Hook Form** - Form handling
- **Zod** - Schema validation
- **date-fns** - Date manipulation
- **lucide-react** - Icon library

## 📁 Proposed Project Structure

```
dnd-frontend/
├── public/
│   └── assets/
│       ├── images/
│       └── icons/
├── src/
│   ├── api/                    # API client and endpoints
│   │   ├── client.ts          # Axios instance with JWT interceptor
│   │   ├── auth.ts            # Authentication endpoints
│   │   ├── characters.ts      # Character endpoints
│   │   ├── campaigns.ts       # Campaign endpoints
│   │   ├── combat.ts          # Combat endpoints
│   │   └── bestiary.ts        # Bestiary endpoints
│   ├── components/            # Reusable components
│   │   ├── ui/               # shadcn/ui components
│   │   ├── layout/           # Layout components
│   │   ├── character/        # Character-related components
│   │   ├── combat/           # Combat components
│   │   └── campaign/         # Campaign components
│   ├── features/             # Feature-based modules
│   │   ├── auth/
│   │   │   ├── Login.tsx
│   │   │   ├── Register.tsx
│   │   │   └── useAuth.ts
│   │   ├── characters/
│   │   │   ├── CharacterList.tsx
│   │   │   ├── CharacterCreate.tsx
│   │   │   ├── CharacterSheet.tsx
│   │   │   └── CharacterLevelUp.tsx
│   │   ├── campaigns/
│   │   │   ├── CampaignList.tsx
│   │   │   ├── CampaignCreate.tsx
│   │   │   ├── CampaignDashboard.tsx
│   │   │   └── PartyStatus.tsx
│   │   ├── combat/
│   │   │   ├── CombatTracker.tsx
│   │   │   ├── InitiativeOrder.tsx
│   │   │   ├── CombatActions.tsx
│   │   │   └── CombatLog.tsx
│   │   └── bestiary/
│   │       ├── BestiaryList.tsx
│   │       └── MonsterCard.tsx
│   ├── hooks/                # Custom React hooks
│   │   ├── useCharacters.ts
│   │   ├── useCampaigns.ts
│   │   ├── useCombat.ts
│   │   └── useAuth.ts
│   ├── types/                # TypeScript types
│   │   ├── character.ts
│   │   ├── campaign.ts
│   │   ├── combat.ts
│   │   └── api.ts
│   ├── store/                # Global state
│   │   └── authStore.ts
│   ├── utils/                # Utility functions
│   │   ├── formatters.ts
│   │   ├── validators.ts
│   │   └── constants.ts
│   ├── pages/                # Page components
│   │   ├── Home.tsx
│   │   ├── Dashboard.tsx
│   │   ├── Characters.tsx
│   │   ├── Campaigns.tsx
│   │   ├── Combat.tsx
│   │   └── Bestiary.tsx
│   ├── App.tsx
│   ├── main.tsx
│   └── index.css
├── package.json
├── tsconfig.json
├── vite.config.ts
└── tailwind.config.js
```

## 🎨 Key Features to Implement

### Phase 1: Foundation (Completed ✅)
1. **Project Architecture**
   - Built with Next.js (App Router, Turbopack) + TypeScript + Tailwind CSS
   - Centralized authentication & user state with Zustand
   - Configured API client with Axios + automatic JWT token refresh interceptors

2. **Authentication Flow**
   - Login, Register, Forgot Password, and Reset Password pages
   - Secure token rotation and persistent session handling
   - Route protection for authenticated portals

3. **Design System & Layout**
   - Medieval/dark fantasy UI aesthetic (`#0c0d12` with radial atmospheric vignettes, `#c5a059` gold filigree accents)
   - Custom UI components: `FantasyCard`, `ParchmentScroll`, `FancyHeaderLogo`, and class heraldry
   - Responsive navbar, account menu, and interactive landing page pillars

### Phase 2: Character Management (Completed ✅)
1. **Character List (`/characters`)**
   - Character dashboard with class heraldry icons, search, level/race filters
   - Card views, quick actions, and deletion safeguards

2. **Character Creation Wizard (`/characters/create`)**
   - Multi-step creation wizard (Basic Info, Ability Scores, Equipment, Spells, Subclass, Personality, Review)
   - Support for point-buy, standard array, and manual score entry
   - Automatic 5E background equipment, weapons, and origin feat assignments

3. **Character Sheet (`/characters/[id]`)**
   - Full attributes, ability scores & modifiers, saving throws, and skill proficiencies
   - Equipment Paperdoll with attunement limits, item slots, and weight/encumbrance calculations
   - Spellbook and spell slot tracker (prepared vs. known casters, ritual casting, slot consumption)
   - Dynamic rest dialogs (Short Rest, Long Rest) and HP management (damage, healing, temp HP)
   - Level-up wizard with ASI, feat choices, and subclass progression

### Phase 3: Gauntlet Arcade & Campaign System (Completed ✅)
1. **Roguelike Gauntlet Pillar (`/gauntlet`)**
   - Wave survival dungeon trial with snapshot characters (protects persistent hero sheets from permanent loss)
   - 10 progressive waves with escalating CR and endless overtime
   - Themed gauntlet arenas (Colosseum of Blades, Crypt of the Undead, Infernal Pit, Savage Wilds, Sunken Dungeon)
   - Respite rewards, tactical boon selections, and high-score survival leaderboards

2. **Legacy Campaign App (Backend Ready)**
   - 5–30 room progressive dungeon crawls with treasure rooms and boss encounters
   - Available via backend endpoints with optional frontend activation

### Phase 4: Tactical Combat Engine (Completed ✅ - v1.13.1)
1. **Interactive BattleGrid & Movement**
   - 2D tactical grid with Chebyshev 5E movement distance calculations
   - Smooth animated token overlay with 450ms CSS coordinate transitions
   - Difficult terrain movement multipliers and visual threat ranges

2. **5E Action Economy & ActionDock**
   - Turn tracker with Action, Bonus Action, Reaction, and Movement economy
   - Weapon attacks with reach/range checking, disadvantage in close-quarters, and thrown weapons
   - Spell casting modal (`SpellCastModal`) with AoE templates (cone, cube, sphere, line) and concentration tracking
   - Active buff mechanics (*Shield*, *Mage Armor*, *Blur*, *Mirror Image*, *False Life*) with AC calculations

3. **Movement-First Tactical Monster AI**
   - Autonomous Round 1 turn execution for monsters winning initiative
   - Reachability scoring (charges into 5 ft melee range before swinging)
   - Archetype tactical spacing (archers/mages maintain 15–60 ft distance and back up when cornered to avoid disadvantage)
   - Dynamic ClashCard showing d20 roll comparisons, advantage/disadvantage, and damage breakdowns

---

### Phase 5: Monster Bestiary & Compendium Browser (Planned 📖)
*Expand beyond in-combat statblock modals into a comprehensive, standalone SRD compendium.*

1. **Dedicated Bestiary Browser (`/bestiary`)**
   - Searchable, filterable directory of all 2,300+ SRD monsters imported from Open5e
   - Multi-attribute filtering:
     - Challenge Rating (CR 0 to 30)
     - Creature Type (Aberration, Beast, Dragon, Undead, Fiend, Humanoid, etc.)
     - Size category (Tiny to Gargantuan)
     - Alignment & Environment/Biome (Forest, Dungeon, Mountain, Desert, Swamp, Urban)
   - Fast sorting by Name, CR, Hit Points, and Armor Class

2. **Rich Monster Statblock Display**
   - Full 5E parchment-styled statblock layout
   - Ability scores, saving throws, damage vulnerabilities, resistances, immunities, and condition immunities
   - Senses (Darkvision, Blindsight, Tremorsense, Truesight) and languages
   - Trait listings, multiattack routines, and parsed actions with dice formula tooltips
   - Legendary Actions, Lair Actions, and Innate Spellcasting breakdowns

3. **Ecosystem & Combat Integration**
   - **"Spawn into Practice Arena"**: Quick-launch button to test any monster or pack in `/combat`
   - **"Add to Gauntlet Custom Wave"**: Bookmark or inject monsters into custom gauntlet trials
   - Comparative stat analysis: side-by-side comparison between multiple monsters

---

### Phase 6: 2.5D Isometric Combat Grid & Environmental Arena System (Planned ⚔️)
*Elevate the tactical battle grid into a rich 2.5D isometric battlefield with custom environmental shapes and interactive cover.*

1. **2.5D Isometric / Angled Viewport**
   - **Angled Camera Projection**:
     - Tilting perspective (e.g. 45°–60° pitch, subtle isometric rotation) to create depth while maintaining strict discrete tile-based Chebyshev movement
     - Dual-view toggle: Instant switch between **Top-Down 2D** (pure tactical overview) and **2.5D Angled Overview** (cinematic depth)
     - Smooth pan and zoom controls for large battlefields
   - **Upright 2.5D Billboard Tokens**:
     - Character miniatures, monster tokens, and spell markers stand upright facing the camera (billboard orientation)
     - Dynamic drop-shadows anchored to ground tiles to indicate elevation, jumping, or flight
     - Active turn rings and aura highlights projected flat on the floor underneath upright tokens

2. **Custom & Environmental Grid Geometries (Non-Rectangular Arenas)**
   - Replace rigid N×M rectangular boxes with irregular, organic tactical layouts:
     - **Chokepoint Corridors**: Narrow 1-2 tile dungeon hallways and cavern tunnels
     - **Circular Arenas & Colosseums**: Radial or polygonal fighting pits with perimeter boundary walls
     - **Chasms & Pits**: Voids, ravines, and bottomless pits that cannot be walked across without flight or jumping
     - **Multi-Room & L-Shaped Layouts**: Interconnected rooms with doorways and vision obstruction
   - Dynamic tile matrix states: `Walkable`, `Void / Pit`, `Difficult Terrain`, `Hazard` (Lava/Acid), and `Impassable Wall`

3. **Dynamic Thematic Grid Backgrounds & Textures**
   - Biome-specific battlemat textures:
     - *Crypt of the Undead*: Cracked flagstones, moss, bone piles, iron grates
     - *Infernal Pit*: Smoldering volcanic obsidian, glowing magma fissures
     - *Colosseum of Blades*: Blood-stained sand, wooden barricades, spectator railings
     - *Sunken Dungeon / Cavern*: Damp stone, puddle reflections, stalagmites
     - *Savage Wilds*: Dense dirt path, foliage borders, fallen logs
   - Layered visual effects: subtle ambient dust particles, lighting gradients, and grid line opacity slider (10% to 100%)

4. **Interactive 2.5D Props & Cover Elements**
   - Tactically meaningful environmental props placed on grid tiles:
     - **Half Cover (+2 AC / Dex saves)**: Low stone walls, crates, barrels, wooden barricades
     - **Three-Quarters Cover (+5 AC / Dex saves)**: Thick stone pillars, portcullises, statue pedestals
     - **Full Cover / Total Line of Sight Block**: Heavy masonry walls, closed dungeon doors
   - Interactive prop manipulation: opening/closing doors, climbing onto elevated ledges, destroying barricades

## 🚀 Getting Started

### 1. Create the Frontend Project

```bash
# Create new Vite project
npm create vite@latest dnd-frontend -- --template react-ts

cd dnd-frontend

# Install dependencies
npm install

# Install additional packages
npm install react-router-dom
npm install @tanstack/react-query
npm install axios
npm install zustand
npm install react-hook-form
npm install zod
npm install @hookform/resolvers
npm install date-fns
npm install framer-motion

# Install Tailwind CSS
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p

# Install shadcn/ui
npx shadcn-ui@latest init
```

### 2. Configure CORS on Backend

Add to `dnd_backend/settings.py`:

```python
INSTALLED_APPS = [
    # ...
    'corsheaders',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # Add this
    # ... other middleware
]

# CORS settings
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",  # Vite default port
    "http://localhost:3000",  # Alternative port
]

CORS_ALLOW_CREDENTIALS = True
```

Install django-cors-headers:
```bash
pip install django-cors-headers
```

### 3. Create API Client

```typescript
// src/api/client.ts
import axios from 'axios';

const API_BASE_URL = 'http://127.0.0.1:8000/api';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add JWT token to requests
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle token refresh on 401
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      // Implement token refresh logic
    }
    return Promise.reject(error);
  }
);
```

## 🎨 UI/UX Design Principles

### Visual Design
- **Dark Mode First**: D&D aesthetic with dark backgrounds
- **Fantasy Theme**: Medieval/fantasy-inspired UI elements
- **Color Palette**:
  - Primary: Deep purple/blue (#4C1D95)
  - Secondary: Gold/amber (#F59E0B)
  - Accent: Emerald green (#10B981)
  - Danger: Red (#EF4444)
  - Background: Dark gray (#1F2937)

### User Experience
- **Responsive**: Mobile-first design
- **Intuitive Navigation**: Clear menu structure
- **Quick Actions**: Common actions easily accessible
- **Real-time Updates**: Live data with React Query
- **Loading States**: Skeleton screens and spinners
- **Error Handling**: Clear error messages

### Accessibility
- **ARIA Labels**: Proper accessibility labels
- **Keyboard Navigation**: Full keyboard support
- **Screen Reader**: Compatible with screen readers
- **Color Contrast**: WCAG AA compliant

## 📊 State Management Strategy

### Server State (React Query)
- Character data
- Campaign data
- Combat state
- Bestiary data
- API responses

### Client State (Zustand/Context)
- User authentication
- UI preferences
- Theme settings
- Navigation state

## 🔐 Authentication Flow

1. User logs in → Receive JWT tokens
2. Store tokens in localStorage
3. Add token to all API requests
4. Refresh token when expired
5. Redirect to login on auth failure

## 📱 Responsive Breakpoints

```css
/* Mobile: 0-640px */
/* Tablet: 641-1024px */
/* Desktop: 1025px+ */
```

## 🧪 Testing Strategy

- **Unit Tests**: Vitest for component testing
- **Integration Tests**: React Testing Library
- **E2E Tests**: Playwright (optional)

## 📈 Performance Optimization

- Code splitting with React.lazy
- Image optimization
- API response caching with React Query
- Memoization with useMemo/useCallback
- Virtual scrolling for long lists

## 🚢 Deployment Options

1. **Vercel** - Recommended for React apps
2. **Netlify** - Alternative hosting
3. **GitHub Pages** - Free static hosting
4. **Docker** - Containerized deployment

## 📝 Next Steps (Roadmap)

1. **Phase 5: Standalone Bestiary Compendium (`/bestiary`)**
   - Build a searchable, filterable monster directory connecting to the backend `/api/bestiary/enemies/` endpoint.
   - Implement parchment statblock cards with complete 5E action, trait, and spellcasting breakdowns.
   - Add "Spawn in Arena" and "Test in Practice Mode" triggers.

2. **Phase 6: 2.5D Isometric Combat Grid & Environmental Arena System**
   - Implement 2.5D angled viewport toggle (`Top-Down 2D` vs `2.5D Isometric View`).
   - Create upright 2.5D billboard token orientation with grounded perspective drop shadows.
   - Add non-rectangular custom grid geometries (chokepoints, circular pits, chasms, corridors).
   - Implement themed battlemat textures and interactive cover/prop obstacles.

## 🎯 Success Metrics

- ✅ User can register, login, and rotate JWT tokens
- ✅ User can create, customize, level up, and manage characters with full paperdoll inventory
- ✅ User can fight wave survival trials in the Roguelike Gauntlet mode
- ✅ Tactical turn-based combat with 5E action economy, movement-first AI, and spell AoE
- ⏳ Dedicated standalone Bestiary Compendium for 2,300+ SRD monsters
- ⏳ 2.5D angled tactical combat arena with custom environmental shapes and cover props
- ✅ Fully responsive across desktop, tablet, and mobile
- ✅ Fast load times with Next.js Turbopack and optimized SSR/SSG caching
