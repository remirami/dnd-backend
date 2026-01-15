from django.contrib import admin
from .models import (
    Encounter, EncounterEnemy, EncounterTheme,
    EnemyThemeAssociation, BiomeEncounterWeight, ThemeIncompatibility
)


class EncounterEnemyInline(admin.TabularInline):
    model = EncounterEnemy
    extra = 1


@admin.register(Encounter)
class EncounterAdmin(admin.ModelAdmin):
    inlines = [EncounterEnemyInline]
    list_display = ('name', 'theme', 'biome', 'is_chaotic', 'created_at')
    list_filter = ('is_chaotic', 'biome', 'theme')
    search_fields = ('name', 'location', 'description')


@admin.register(EncounterEnemy)
class EncounterEnemyAdmin(admin.ModelAdmin):
    list_display = ('name', 'encounter', 'enemy', 'initiative', 'current_hp', 'is_alive')
    list_filter = ('is_alive',)


@admin.register(EncounterTheme)
class EncounterThemeAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'min_cr', 'max_cr', 'weight')
    list_filter = ('category',)
    search_fields = ('name', 'description')


@admin.register(EnemyThemeAssociation)
class EnemyThemeAssociationAdmin(admin.ModelAdmin):
    list_display = ('enemy', 'theme', 'role', 'weight')
    list_filter = ('role', 'theme')
    search_fields = ('enemy__name', 'theme__name')


@admin.register(BiomeEncounterWeight)
class BiomeEncounterWeightAdmin(admin.ModelAdmin):
    list_display = ('theme', 'biome', 'category', 'weight')
    list_filter = ('biome', 'category')
    search_fields = ('theme__name',)


@admin.register(ThemeIncompatibility)
class ThemeIncompatibilityAdmin(admin.ModelAdmin):
    list_display = ('theme1', 'theme2', 'allow_chaotic')
    list_filter = ('allow_chaotic',)
