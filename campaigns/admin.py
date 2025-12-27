from django.contrib import admin
from .models import Campaign, CampaignCharacter, CampaignEncounter, TreasureRoom, TreasureRoomReward, RecruitableCharacter, RecruitmentRoom


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
    list_display = ('name', 'status', 'start_mode', 'starting_level', 'current_encounter_index', 'total_encounters', 'long_rests_used', 'long_rests_available', 'created_at')
    list_filter = ('status', 'start_mode', 'starting_level', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'started_at', 'ended_at')
    inlines = [CampaignCharacterInline, CampaignEncounterInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'status', 'notes')
        }),
        ('Roguelite Settings', {
            'fields': ('starting_level', 'start_mode', 'starting_party_size')
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


@admin.register(RecruitableCharacter)
class RecruitableCharacterAdmin(admin.ModelAdmin):
    list_display = ('name', 'character_class', 'race', 'rarity', 'created_at')
    list_filter = ('rarity', 'character_class', 'race', 'created_at')
    search_fields = ('name', 'recruitment_description', 'personality_trait')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'character_class', 'race', 'background')
        }),
        ('Recruitment Info', {
            'fields': ('recruitment_description', 'personality_trait', 'rarity')
        }),
        ('Starting Stats', {
            'fields': ('starting_stats', 'starting_equipment'),
            'description': 'Starting stats and equipment for this recruit template'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(RecruitmentRoom)
class RecruitmentRoomAdmin(admin.ModelAdmin):
    list_display = ('campaign', 'encounter_number', 'discovered', 'recruit_selected', 'created_at')
    list_filter = ('discovered', 'campaign', 'created_at')
    search_fields = ('campaign__name',)
    readonly_fields = ('created_at', 'discovered_at')
    filter_horizontal = ('available_recruits',)
    
    fieldsets = (
        ('Campaign', {
            'fields': ('campaign', 'encounter_number')
        }),
        ('Recruitment', {
            'fields': ('available_recruits', 'discovered', 'recruit_selected')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'discovered_at')
        }),
    )


class TreasureRoomRewardInline(admin.TabularInline):
    model = TreasureRoomReward
    extra = 0
    fields = ('item', 'quantity', 'gold_amount', 'xp_bonus', 'claimed_by', 'claimed_at')
    readonly_fields = ('claimed_at',)


@admin.register(TreasureRoom)
class TreasureRoomAdmin(admin.ModelAdmin):
    list_display = ('campaign', 'encounter_number', 'room_type', 'discovered', 'loot_distributed', 'created_at')
    list_filter = ('room_type', 'discovered', 'loot_distributed', 'campaign', 'created_at')
    search_fields = ('campaign__name',)
    readonly_fields = ('created_at', 'discovered_at')
    inlines = [TreasureRoomRewardInline]
    
    fieldsets = (
        ('Campaign', {
            'fields': ('campaign', 'encounter_number', 'room_type')
        }),
        ('Status', {
            'fields': ('discovered', 'loot_distributed', 'rewards')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'discovered_at')
        }),
    )


@admin.register(TreasureRoomReward)
class TreasureRoomRewardAdmin(admin.ModelAdmin):
    list_display = ('treasure_room', 'item', 'quantity', 'gold_amount', 'xp_bonus', 'claimed_by', 'claimed_at', 'is_claimed')
    list_filter = ('treasure_room__campaign', 'claimed_at')
    search_fields = ('treasure_room__campaign__name', 'item__name', 'claimed_by__character__name')
    readonly_fields = ('claimed_at',)
    
    def is_claimed(self, obj):
        return obj.claimed_by is not None
    is_claimed.boolean = True
    is_claimed.short_description = 'Claimed'
    
    fieldsets = (
        ('Treasure Room', {
            'fields': ('treasure_room',)
        }),
        ('Reward', {
            'fields': ('item', 'quantity', 'gold_amount', 'xp_bonus')
        }),
        ('Claiming', {
            'fields': ('claimed_by', 'claimed_at')
        }),
    )
