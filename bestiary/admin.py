from django.contrib import admin

from .models import (
    Condition,
    DamageType,
    Enemy,
    EnemyAbility,
    EnemyAction,
    EnemyActionDamage,
    EnemyAttack,
    EnemyConditionImmunity,
    EnemyEnvironment,
    EnemyLanguage,
    EnemyLegendaryAction,
    EnemyMultiattack,
    EnemyResistance,
    EnemySpell,
    EnemySpellSlot,
    EnemyStats,
    EnemyTrait,
    EnemyTreasure,
    Environment,
    Language,
)


class EnemyActionDamageInline(admin.TabularInline):
    model = EnemyActionDamage
    extra = 1


@admin.register(EnemyAction)
class EnemyActionAdmin(admin.ModelAdmin):
    list_display = ('enemy', 'name', 'action_type', 'attack_type', 'attack_bonus', 'saving_throw_dc', 'has_recharge')
    list_filter = ('action_type', 'attack_type', 'has_recharge')
    search_fields = ('name', 'enemy__name')
    inlines = [EnemyActionDamageInline]


class EnemyActionInline(admin.TabularInline):
    model = EnemyAction
    extra = 0
    show_change_link = True


class EnemyMultiattackInline(admin.StackedInline):
    model = EnemyMultiattack
    extra = 0


class EnemyTraitInline(admin.TabularInline):
    model = EnemyTrait
    extra = 1


class EnemyAttackInline(admin.TabularInline):
    model = EnemyAttack

class EnemyAbilityInline(admin.TabularInline):
    model = EnemyAbility

class EnemySpellInline(admin.TabularInline):
    model = EnemySpell


class EnemySpellSlotInline(admin.TabularInline):
    model = EnemySpellSlot


class EnemyStatsInline(admin.StackedInline):
    model = EnemyStats
    fieldsets = (
        ('Ability Scores', {
            'fields': ('strength', 'dexterity', 'constitution', 'intelligence', 'wisdom', 'charisma')
        }),
        ('Combat Stats', {
            'fields': ('hit_points', 'armor_class', 'speed')
        }),
        ('Saving Throws', {
            'fields': ('str_save', 'dex_save', 'con_save', 'int_save', 'wis_save', 'cha_save'),
            'classes': ('collapse',)
        }),
        ('Skills', {
            'fields': ('athletics', 'acrobatics', 'sleight_of_hand', 'stealth', 'arcana', 'history', 
                      'investigation', 'nature', 'religion', 'animal_handling', 'insight', 'medicine', 
                      'perception', 'survival', 'deception', 'intimidation', 'performance', 'persuasion'),
            'classes': ('collapse',)
        }),
        ('Senses & Perception', {
            'fields': ('darkvision', 'blindsight', 'tremorsense', 'truesight', 'passive_perception')
        }),
        ('Spellcasting', {
            'fields': ('spell_save_dc', 'spell_attack_bonus')
        }),
    )


class EnemyResistanceInline(admin.TabularInline):
    model = EnemyResistance
    extra = 1


class EnemyLanguageInline(admin.TabularInline):
    model = EnemyLanguage
    extra = 1


class EnemyConditionImmunityInline(admin.TabularInline):
    model = EnemyConditionImmunity
    extra = 1


class EnemyLegendaryActionInline(admin.TabularInline):
    model = EnemyLegendaryAction
    extra = 1


class EnemyEnvironmentInline(admin.TabularInline):
    model = EnemyEnvironment
    extra = 1


class EnemyTreasureInline(admin.TabularInline):
    model = EnemyTreasure
    extra = 1


@admin.register(Enemy)
class EnemyAdmin(admin.ModelAdmin):
    fields = ('name', 'challenge_rating', 'size', 'creature_type', 'alignment')
    inlines = [
        EnemyStatsInline, EnemyActionInline, EnemyMultiattackInline, EnemyTraitInline,
        EnemyAttackInline, EnemyAbilityInline, EnemySpellInline, 
        EnemyResistanceInline, EnemyLanguageInline, EnemyConditionImmunityInline,
        EnemyLegendaryActionInline, EnemyEnvironmentInline, EnemyTreasureInline
    ]
    list_display = ('name', 'hp', 'ac', 'challenge_rating', 'size', 'creature_type', 'alignment')
    list_filter = ('challenge_rating', 'size', 'creature_type', 'alignment')
    search_fields = ('name',)


@admin.register(EnemySpell)
class EnemySpellAdmin(admin.ModelAdmin):
    inlines = [EnemySpellSlotInline]


@admin.register(DamageType)
class DamageTypeAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(Language)
class LanguageAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(Condition)
class ConditionAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(Environment)
class EnvironmentAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
