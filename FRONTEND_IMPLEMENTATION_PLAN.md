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

### Phase 1: Foundation (Week 1-2)
1. **Project Setup**
   - Initialize Vite + React + TypeScript
   - Configure Tailwind CSS and shadcn/ui
   - Set up routing with React Router
   - Configure API client with Axios

2. **Authentication**
   - Login page
   - Registration page
   - JWT token management
   - Protected routes
   - Auto token refresh

3. **Basic Layout**
   - Navigation bar
   - Sidebar
   - Footer
   - Responsive design

### Phase 2: Character Management (Week 3-4)
1. **Character List**
   - Display all user's characters
   - Character cards with key stats
   - Filter and search

2. **Character Creation**
   - Step-by-step wizard
   - Class selection
   - Race selection
   - Background selection
   - Ability score assignment
   - Equipment selection

3. **Character Sheet**
   - Full character display
   - Stats and modifiers
   - Features and abilities
   - Inventory
   - Spells (for casters)
   - Edit capabilities

4. **Level Up**
   - Level up interface
   - Feature selection
   - ASI or Feat choice
   - Subclass selection

### Phase 3: Campaign System (Week 5-6)
1. **Campaign List**
   - Display all campaigns
   - Create new campaign
   - Campaign cards with progress

2. **Campaign Dashboard**
   - Party status
   - Current encounter
   - XP tracking
   - Treasure rooms
   - Rest management

3. **Encounter Management**
   - Start encounter
   - Complete encounter
   - Rewards display

### Phase 4: Combat System (Week 7-8)
1. **Combat Tracker**
   - Initiative order
   - Turn management
   - HP tracking
   - Condition tracking

2. **Combat Actions**
   - Attack interface
   - Spell casting
   - Movement
   - Reactions

3. **Combat Log**
   - Real-time action log
   - Damage rolls
   - Save results
   - Export functionality

### Phase 5: Additional Features (Week 9-10)
1. **Bestiary Browser**
   - Monster list
   - Monster details
   - Search and filter

2. **Spell Management**
   - Spell list
   - Spell preparation
   - Spell slots tracking

3. **Multiclassing**
   - Multiclass interface
   - Spell slot calculation display
   - Hit dice tracking

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

## 📝 Next Steps

1. **Set up the project** using the commands above
2. **Implement authentication** (login/register)
3. **Create character list** page
4. **Build character creation** wizard
5. **Implement campaign dashboard**
6. **Add combat tracker**

## 🎯 Success Metrics

- ✅ User can register and login
- ✅ User can create and view characters
- ✅ User can create and manage campaigns
- ✅ User can run combat encounters
- ✅ All backend features accessible via UI
- ✅ Responsive on mobile, tablet, desktop
- ✅ Fast load times (<2s initial load)

---

**Ready to start?** Let me know which phase you'd like to begin with, or if you'd like me to help set up the initial project structure!
