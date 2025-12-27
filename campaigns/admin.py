from django.contrib import admin
from .models import Campaign, CampaignCharacter, CampaignEncounter


class CampaignCharacterInline(admin.TabularInline):
    model = CampaignCharacter
    extra = 0
    fields = ('character', 'current_hp', 'max_hp', 'is_alive', 'hit_dice_remaining')
    readonly_fields = ('created_at', 'updated_at')


class CampaignEncounterInline(admin.TabularInline):
    model = CampaignEncounter
    extra = 0
    fields = ('encounter', 'encounter_number', 'status', 'combat_session')
    readonly_fields = ('completed_at',)


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ('name', 'status', 'current_encounter_index', 'total_encounters', 'long_rests_used', 'long_rests_available', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'started_at', 'ended_at')
    inlines = [CampaignCharacterInline, CampaignEncounterInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'status', 'notes')
        }),
        ('Progress', {
            'fields': ('current_encounter_index', 'total_encounters')
        }),
        ('Rest Management', {
            'fields': ('short_rests_used', 'long_rests_used', 'long_rests_available')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'started_at', 'ended_at')
        }),
    )


@admin.register(CampaignCharacter)
class CampaignCharacterAdmin(admin.ModelAdmin):
    list_display = ('character', 'campaign', 'current_hp', 'max_hp', 'is_alive', 'get_available_hit_dice', 'updated_at')
    list_filter = ('is_alive', 'campaign', 'created_at')
    search_fields = ('character__name', 'campaign__name')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Character', {
            'fields': ('campaign', 'character')
        }),
        ('Status', {
            'fields': ('current_hp', 'max_hp', 'is_alive', 'died_in_encounter')
        }),
        ('Resources', {
            'fields': ('hit_dice_remaining', 'spell_slots')
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def get_available_hit_dice(self, obj):
        return obj.get_available_hit_dice()
    get_available_hit_dice.short_description = 'Hit Dice'


@admin.register(CampaignEncounter)
class CampaignEncounterAdmin(admin.ModelAdmin):
    list_display = ('campaign', 'encounter_number', 'encounter', 'status', 'combat_session', 'completed_at')
    list_filter = ('status', 'campaign', 'completed_at')
    search_fields = ('campaign__name', 'encounter__name')
    readonly_fields = ('completed_at',)
    
    fieldsets = (
        ('Campaign', {
            'fields': ('campaign', 'encounter', 'encounter_number')
        }),
        ('Status', {
            'fields': ('status', 'combat_session', 'completed_at')
        }),
        ('Rewards', {
            'fields': ('rewards',)
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
    )
