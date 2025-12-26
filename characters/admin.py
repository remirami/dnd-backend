from django.contrib import admin
from .models import (
    Character, CharacterStats, CharacterClass, CharacterRace, CharacterBackground,
    CharacterProficiency, CharacterFeature, CharacterSpell, CharacterResistance
)


class CharacterStatsInline(admin.StackedInline):
    model = CharacterStats
    fieldsets = (
        ('Ability Scores', {
            'fields': ('strength', 'dexterity', 'constitution', 'intelligence', 'wisdom', 'charisma')
        }),
        ('Combat Stats', {
            'fields': ('hit_points', 'max_hit_points', 'armor_class', 'speed', 'initiative')
        }),
        ('Hit Dice', {
            'fields': ('hit_dice_total', 'hit_dice_current')
        }),
        ('Senses', {
            'fields': ('darkvision', 'passive_perception', 'passive_investigation', 'passive_insight')
        }),
        ('Spellcasting', {
            'fields': ('spell_save_dc', 'spell_attack_bonus'),
            'classes': ('collapse',)
        }),
    )


class CharacterProficiencyInline(admin.TabularInline):
    model = CharacterProficiency
    extra = 1


class CharacterFeatureInline(admin.TabularInline):
    model = CharacterFeature
    extra = 1


class CharacterSpellInline(admin.TabularInline):
    model = CharacterSpell
    extra = 1


class CharacterResistanceInline(admin.TabularInline):
    model = CharacterResistance
    extra = 1


@admin.register(Character)
class CharacterAdmin(admin.ModelAdmin):
    inlines = [
        CharacterStatsInline, CharacterProficiencyInline, CharacterFeatureInline,
        CharacterSpellInline, CharacterResistanceInline
    ]
    list_display = ('name', 'level', 'character_class', 'race', 'background', 'alignment', 'created_at')
    list_filter = ('level', 'character_class', 'race', 'background', 'alignment', 'created_at')
    search_fields = ('name', 'player_name')
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'player_name', 'level', 'experience_points')
        }),
        ('Character Details', {
            'fields': ('character_class', 'race', 'background', 'size', 'alignment')
        }),
        ('Description', {
            'fields': ('description', 'backstory'),
            'classes': ('collapse',)
        }),
    )


@admin.register(CharacterClass)
class CharacterClassAdmin(admin.ModelAdmin):
    list_display = ('name', 'hit_dice', 'primary_ability')
    search_fields = ('name',)


@admin.register(CharacterRace)
class CharacterRaceAdmin(admin.ModelAdmin):
    list_display = ('name', 'size', 'speed')
    search_fields = ('name',)


@admin.register(CharacterBackground)
class CharacterBackgroundAdmin(admin.ModelAdmin):
    list_display = ('name', 'skill_proficiencies', 'languages')
    search_fields = ('name',)


@admin.register(CharacterStats)
class CharacterStatsAdmin(admin.ModelAdmin):
    list_display = ('character', 'hit_points', 'max_hit_points', 'armor_class')
    search_fields = ('character__name',)


@admin.register(CharacterProficiency)
class CharacterProficiencyAdmin(admin.ModelAdmin):
    list_display = ('character', 'proficiency_type', 'proficiency_level', 'skill_name', 'item_name', 'source')
    list_filter = ('proficiency_type', 'proficiency_level', 'source')
    search_fields = ('character__name', 'skill_name', 'item_name')


@admin.register(CharacterFeature)
class CharacterFeatureAdmin(admin.ModelAdmin):
    list_display = ('character', 'name', 'feature_type', 'source')
    list_filter = ('feature_type',)
    search_fields = ('character__name', 'name', 'source')


@admin.register(CharacterSpell)
class CharacterSpellAdmin(admin.ModelAdmin):
    list_display = ('character', 'name', 'level', 'school', 'is_prepared', 'is_ritual')
    list_filter = ('level', 'school', 'is_prepared', 'is_ritual')
    search_fields = ('character__name', 'name')


@admin.register(CharacterResistance)
class CharacterResistanceAdmin(admin.ModelAdmin):
    list_display = ('character', 'damage_type', 'resistance_type', 'source')
    list_filter = ('resistance_type', 'source')
    search_fields = ('character__name', 'damage_type__name')
