from django.contrib import admin
from .models import MerchantEncounter, MerchantInventoryItem, MerchantTransaction


@admin.register(MerchantEncounter)
class MerchantEncounterAdmin(admin.ModelAdmin):
    list_display = ['merchant_name', 'campaign', 'encounter_number', 'is_active', 'discovered_at']
    list_filter = ['is_active', 'discovered_at', 'campaign']
    search_fields = ['merchant_name', 'campaign__name']
    readonly_fields = ['discovered_at']


@admin.register(MerchantInventoryItem)
class MerchantInventoryItemAdmin(admin.ModelAdmin):
    list_display = ['item', 'merchant', 'price', 'quantity', 'is_sold', 'purchased_by']
    list_filter = ['is_sold', 'merchant__campaign']
    search_fields = ['item__name', 'merchant__merchant_name']
    readonly_fields = ['purchased_at']


@admin.register(MerchantTransaction)
class MerchantTransactionAdmin(admin.ModelAdmin):
    list_display = ['item_name', 'campaign_character', 'price', 'merchant', 'purchased_at']
    list_filter = ['purchased_at', 'merchant__campaign']
    search_fields = ['item_name', 'campaign_character__character__name']
    readonly_fields = ['purchased_at']
