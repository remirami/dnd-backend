from django.contrib import admin
from .models import CombatSession, CombatParticipant, CombatAction, CombatLog


class CombatParticipantInline(admin.TabularInline):
    model = CombatParticipant
    extra = 0
    fields = ('participant_type', 'character', 'encounter_enemy', 'initiative', 'current_hp', 'is_active')


class CombatActionInline(admin.TabularInline):
    model = CombatAction
    extra = 0
    readonly_fields = ('created_at',)
    fields = ('actor', 'action_type', 'target', 'attack_name', 'hit', 'damage_amount', 'round_number', 'created_at')


@admin.register(CombatSession)
class CombatSessionAdmin(admin.ModelAdmin):
    inlines = [CombatParticipantInline, CombatActionInline]
    list_display = ('encounter', 'status', 'current_round', 'current_turn_index', 'started_at')
    list_filter = ('status', 'started_at')
    search_fields = ('encounter__name',)
    readonly_fields = ('started_at', 'ended_at')


@admin.register(CombatParticipant)
class CombatParticipantAdmin(admin.ModelAdmin):
    list_display = ('get_name', 'combat_session', 'participant_type', 'initiative', 'current_hp', 'is_active')
    list_filter = ('participant_type', 'is_active', 'combat_session__status')
    search_fields = ('character__name', 'encounter_enemy__name')
    
    def get_name(self, obj):
        return obj.get_name()
    get_name.short_description = 'Name'


@admin.register(CombatAction)
class CombatActionAdmin(admin.ModelAdmin):
    list_display = ('actor', 'action_type', 'target', 'attack_name', 'hit', 'damage_amount', 'round_number', 'created_at')
    list_filter = ('action_type', 'hit', 'critical', 'round_number', 'created_at')
    search_fields = ('actor__character__name', 'actor__encounter_enemy__name', 'attack_name')
    readonly_fields = ('created_at',)


@admin.register(CombatLog)
class CombatLogAdmin(admin.ModelAdmin):
    list_display = ('combat_session', 'total_rounds', 'total_turns', 'total_damage_dealt', 'total_damage_received', 'created_at')
    list_filter = ('created_at', 'is_public')
    search_fields = ('combat_session__encounter__name',)
    readonly_fields = ('created_at', 'updated_at')
