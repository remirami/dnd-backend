from django.contrib import admin
from .models import Encounter, EncounterEnemy

class EncounterEnemyInline(admin.TabularInline):
    model = EncounterEnemy
    extra = 1

@admin.register(Encounter)
class EncounterAdmin(admin.ModelAdmin):
    inlines = [EncounterEnemyInline]
    list_display = ('name', 'location', 'created_at')
    search_fields = ('name', 'location')

@admin.register(EncounterEnemy)
class EncounterEnemyAdmin(admin.ModelAdmin):
    list_display = ('name', 'encounter', 'enemy', 'initiative', 'current_hp', 'is_alive')
    list_filter = ('is_alive',)
