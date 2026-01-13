from rest_framework import serializers
from .models import MerchantEncounter, MerchantInventoryItem, MerchantTransaction
from items.serializers import ItemSerializer
from campaigns.serializers import CampaignCharacterSerializer


class MerchantInventoryItemSerializer(serializers.ModelSerializer):
    """Serializer for merchant inventory items"""
    item_name = serializers.CharField(source='item.name', read_only=True)
    item_details = ItemSerializer(source='item', read_only=True)
    item_rarity = serializers.CharField(source='item.rarity', read_only=True)
    purchased_by_name = serializers.CharField(source='purchased_by.character.name', read_only=True, allow_null=True)
    
    class Meta:
        model = MerchantInventoryItem
        fields = '__all__'


class MerchantEncounterSerializer(serializers.ModelSerializer):
    """Serializer for merchant encounters"""
    inventory = MerchantInventoryItemSerializer(many=True, read_only=True)
    available_items_count = serializers.SerializerMethodField()
    sold_items_count = serializers.SerializerMethodField()
    campaign_name = serializers.CharField(source='campaign.name', read_only=True)
    
    class Meta:
        model = MerchantEncounter
        fields = '__all__'
    
    def get_available_items_count(self, obj):
        """Get count of unsold items"""
        return obj.inventory.filter(is_sold=False).count()
    
    def get_sold_items_count(self, obj):
        """Get count of sold items"""
        return obj.inventory.filter(is_sold=True).count()


class MerchantTransactionSerializer(serializers.ModelSerializer):
    """Serializer for merchant transactions"""
    character_name = serializers.CharField(source='campaign_character.character.name', read_only=True)
    merchant_name = serializers.CharField(source='merchant.merchant_name', read_only=True)
    
    class Meta:
        model = MerchantTransaction
        fields = '__all__'


class PurchaseItemSerializer(serializers.Serializer):
    """Serializer for purchase request"""
    inventory_item_id = serializers.IntegerField(required=True, help_text="ID of the inventory item to purchase")
    campaign_character_id = serializers.IntegerField(required=True, help_text="ID of the character making the purchase")
