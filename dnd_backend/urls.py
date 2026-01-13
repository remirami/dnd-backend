"""
URL configuration for dnd_backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from bestiary.views import EnemyViewSet, import_monsters_view
from encounters.views import EncounterViewSet, EncounterEnemyViewSet
from characters.views import (
    CharacterViewSet, CharacterClassViewSet, CharacterRaceViewSet,
    CharacterBackgroundViewSet, CharacterStatsViewSet, CharacterProficiencyViewSet,
    CharacterFeatureViewSet, CharacterSpellViewSet, CharacterResistanceViewSet
)
from combat.views import CombatSessionViewSet, CombatParticipantViewSet, CombatActionViewSet, CombatLogViewSet
from items.views import (
    ItemViewSet, WeaponViewSet, ArmorViewSet, ConsumableViewSet,
    MagicItemViewSet, ItemCategoryViewSet, ItemPropertyViewSet
)
from campaigns.views import CampaignViewSet, CampaignCharacterViewSet, CampaignEncounterViewSet
from spells.views import SpellViewSet
from merchants.views import MerchantViewSet


router = DefaultRouter()
# Bestiary routes
router.register(r'enemies', EnemyViewSet, basename='enemy')
# Encounter system routes
router.register(r'encounters', EncounterViewSet, basename='encounter')
router.register(r'encounter-enemies', EncounterEnemyViewSet, basename='encounter-enemy')
# Character management routes
router.register(r'characters', CharacterViewSet, basename='character')
router.register(r'character-classes', CharacterClassViewSet, basename='character-class')
router.register(r'character-races', CharacterRaceViewSet, basename='character-race')
router.register(r'character-backgrounds', CharacterBackgroundViewSet, basename='character-background')
router.register(r'character-stats', CharacterStatsViewSet, basename='character-stats')
router.register(r'character-proficiencies', CharacterProficiencyViewSet, basename='character-proficiency')
router.register(r'character-features', CharacterFeatureViewSet, basename='character-feature')
router.register(r'character-spells', CharacterSpellViewSet, basename='character-spell')
router.register(r'character-resistances', CharacterResistanceViewSet, basename='character-resistance')
# Combat system routes
router.register(r'combat/sessions', CombatSessionViewSet, basename='combat-session')
router.register(r'combat/participants', CombatParticipantViewSet, basename='combat-participant')
router.register(r'combat/actions', CombatActionViewSet, basename='combat-action')
router.register(r'combat/logs', CombatLogViewSet, basename='combat-log')
# Items system routes
router.register(r'items', ItemViewSet, basename='item')
router.register(r'weapons', WeaponViewSet, basename='weapon')
router.register(r'armor', ArmorViewSet, basename='armor')
router.register(r'consumables', ConsumableViewSet, basename='consumable')
router.register(r'magic-items', MagicItemViewSet, basename='magic-item')
router.register(r'item-categories', ItemCategoryViewSet, basename='item-category')
router.register(r'item-properties', ItemPropertyViewSet, basename='item-property')
# Campaign system routes
router.register(r'campaigns', CampaignViewSet, basename='campaign')
router.register(r'campaign-characters', CampaignCharacterViewSet, basename='campaign-character')
router.register(r'campaign-encounters', CampaignEncounterViewSet, basename='campaign-encounter')
# Spell library routes
router.register(r'spells', SpellViewSet, basename='spell')
# Merchant/shop system routes
router.register(r'merchants', MerchantViewSet, basename='merchant')


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('authentication.urls')),
    path('api/enemies/import/', import_monsters_view, name='import_monsters'),
    path('api/', include(router.urls)),
]
