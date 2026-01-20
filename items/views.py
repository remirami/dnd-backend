from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Item, Weapon, Armor, Consumable, MagicItem, ItemCategory, ItemProperty
from .serializers import (
    ItemSerializer, WeaponSerializer, ArmorSerializer, ConsumableSerializer,
    MagicItemSerializer, ItemCategorySerializer, ItemPropertySerializer
)


class ItemCategoryViewSet(viewsets.ModelViewSet):
    """API endpoint for item categories"""
    queryset = ItemCategory.objects.all()
    serializer_class = ItemCategorySerializer


class ItemPropertyViewSet(viewsets.ModelViewSet):
    """API endpoint for item properties"""
    queryset = ItemProperty.objects.all()
    serializer_class = ItemPropertySerializer


class ItemViewSet(viewsets.ModelViewSet):
    """API endpoint for base items"""
    queryset = Item.objects.all()
    serializer_class = ItemSerializer
    
    def get_queryset(self):
        queryset = Item.objects.all()
        search = self.request.query_params.get('search', None)
        category = self.request.query_params.get('category', None)
        rarity = self.request.query_params.get('rarity', None)
        is_magical = self.request.query_params.get('is_magical', None)
        
        if search:
            queryset = queryset.filter(name__icontains=search)
        if category:
            queryset = queryset.filter(category__name__icontains=category)
        if rarity:
            queryset = queryset.filter(rarity=rarity)
        if is_magical is not None:
            queryset = queryset.filter(is_magical=is_magical.lower() == 'true')
        
        return queryset.order_by('name')


class WeaponViewSet(viewsets.ModelViewSet):
    """API endpoint for weapons"""
    queryset = Weapon.objects.all()
    serializer_class = WeaponSerializer
    
    def get_queryset(self):
        queryset = Weapon.objects.all()
        weapon_type = self.request.query_params.get('weapon_type', None)
        finesse = self.request.query_params.get('finesse', None)
        
        if weapon_type:
            queryset = queryset.filter(weapon_type=weapon_type)
        if finesse is not None:
            queryset = queryset.filter(finesse=finesse.lower() == 'true')
        
        return queryset


class ArmorViewSet(viewsets.ModelViewSet):
    """API endpoint for armor"""
    queryset = Armor.objects.all()
    serializer_class = ArmorSerializer
    
    def get_queryset(self):
        queryset = Armor.objects.all()
        armor_type = self.request.query_params.get('armor_type', None)
        
        if armor_type:
            queryset = queryset.filter(armor_type=armor_type)
        
        return queryset


class ConsumableViewSet(viewsets.ModelViewSet):
    """API endpoint for consumables"""
    queryset = Consumable.objects.all()
    serializer_class = ConsumableSerializer
    
    def get_queryset(self):
        queryset = Consumable.objects.all()
        consumable_type = self.request.query_params.get('consumable_type', None)
        
        if consumable_type:
            queryset = queryset.filter(consumable_type=consumable_type)
        
        return queryset


class MagicItemViewSet(viewsets.ModelViewSet):
    """API endpoint for magic items"""
    queryset = MagicItem.objects.all()
    serializer_class = MagicItemSerializer
    
    def get_queryset(self):
        queryset = MagicItem.objects.all()
        rarity = self.request.query_params.get('rarity', None)
        attunement_required = self.request.query_params.get('attunement_required', None)
        
        if rarity:
            queryset = queryset.filter(rarity=rarity)
        if attunement_required is not None:
            queryset = queryset.filter(attunement_required=attunement_required.lower() == 'true')
        
        return queryset
