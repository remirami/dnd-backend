from rest_framework import serializers
from .models import Item, Weapon, Armor, Consumable, MagicItem, ItemCategory, ItemProperty


class ItemPropertySerializer(serializers.ModelSerializer):
    """Serializer for item properties"""
    class Meta:
        model = ItemProperty
        fields = '__all__'


class ItemCategorySerializer(serializers.ModelSerializer):
    """Serializer for item categories"""
    class Meta:
        model = ItemCategory
        fields = '__all__'


class ItemSerializer(serializers.ModelSerializer):
    """Base item serializer"""
    category = ItemCategorySerializer(read_only=True)
    category_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    properties = ItemPropertySerializer(many=True, read_only=True)
    property_ids = serializers.PrimaryKeyRelatedField(
        many=True, queryset=ItemProperty.objects.all(), write_only=True, required=False
    )
    rarity_display = serializers.CharField(source='get_rarity_display', read_only=True)
    
    class Meta:
        model = Item
        fields = '__all__'
    
    def create(self, validated_data):
        property_ids = validated_data.pop('property_ids', [])
        item = Item.objects.create(**validated_data)
        if property_ids:
            item.properties.set(property_ids)
        return item
    
    def update(self, instance, validated_data):
        property_ids = validated_data.pop('property_ids', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if property_ids is not None:
            instance.properties.set(property_ids)
        return instance


class WeaponSerializer(ItemSerializer):
    """Serializer for weapons"""
    weapon_type_display = serializers.CharField(source='get_weapon_type_display', read_only=True)
    damage_type = serializers.StringRelatedField(read_only=True)
    damage_type_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    
    class Meta:
        model = Weapon
        fields = '__all__'


class ArmorSerializer(ItemSerializer):
    """Serializer for armor"""
    armor_type_display = serializers.CharField(source='get_armor_type_display', read_only=True)
    
    class Meta:
        model = Armor
        fields = '__all__'


class ConsumableSerializer(ItemSerializer):
    """Serializer for consumables"""
    consumable_type_display = serializers.CharField(source='get_consumable_type_display', read_only=True)
    
    class Meta:
        model = Consumable
        fields = '__all__'


class MagicItemSerializer(ItemSerializer):
    """Serializer for magic items"""
    
    class Meta:
        model = MagicItem
        fields = '__all__'

