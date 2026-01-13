from django.contrib import admin
from .models import Spell, SpellDamage


@admin.register(Spell)
class SpellAdmin(admin.ModelAdmin):
    list_display = ['name', 'level', 'school', 'casting_time', 'concentration', 'ritual']
    list_filter = ['level', 'school', 'concentration', 'ritual', 'classes']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    filter_horizontal = ['classes']
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'level', 'school')
        }),
        ('Casting Information', {
            'fields': ('casting_time', 'range', 'components', 'material', 'duration', 'concentration', 'ritual')
        }),
        ('Effects', {
            'fields': ('description', 'higher_level')
        }),
        ('Availability', {
            'fields': ('classes', 'source', 'page')
        }),
    )


@admin.register(SpellDamage)
class SpellDamageAdmin(admin.ModelAdmin):
    list_display = ['spell', 'spell_slot_level', 'damage_dice', 'damage_type']
    list_filter = ['damage_type', 'spell_slot_level']
    search_fields = ['spell__name']
