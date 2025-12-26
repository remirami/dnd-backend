from django.contrib import admin
from .models import Item, Weapon, Armor, Consumable, MagicItem, ItemCategory, ItemProperty


@admin.register(ItemCategory)
class ItemCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'description']
    search_fields = ['name']


@admin.register(ItemProperty)
class ItemPropertyAdmin(admin.ModelAdmin):
    list_display = ['name', 'description']
    search_fields = ['name']


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'rarity', 'is_magical', 'value', 'weight']
    list_filter = ['category', 'rarity', 'is_magical', 'requires_attunement']
    search_fields = ['name', 'description']
    filter_horizontal = ['properties']


@admin.register(Weapon)
class WeaponAdmin(admin.ModelAdmin):
    list_display = ['name', 'weapon_type', 'damage_dice', 'damage_type', 'finesse', 'two_handed']
    list_filter = ['weapon_type', 'finesse', 'two_handed', 'thrown', 'ammunition']
    search_fields = ['name', 'description']


@admin.register(Armor)
class ArmorAdmin(admin.ModelAdmin):
    list_display = ['name', 'armor_type', 'base_ac', 'max_dex_bonus', 'min_strength', 'stealth_disadvantage']
    list_filter = ['armor_type', 'stealth_disadvantage']
    search_fields = ['name', 'description']


@admin.register(Consumable)
class ConsumableAdmin(admin.ModelAdmin):
    list_display = ['name', 'consumable_type', 'effect', 'duration']
    list_filter = ['consumable_type']
    search_fields = ['name', 'effect']


@admin.register(MagicItem)
class MagicItemAdmin(admin.ModelAdmin):
    list_display = ['name', 'rarity', 'attunement_required', 'bonus_to_hit', 'bonus_to_damage', 'bonus_to_ac']
    list_filter = ['rarity', 'attunement_required', 'requires_attunement']
    search_fields = ['name', 'description', 'spell_effect']
