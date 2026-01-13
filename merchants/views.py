from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from .models import MerchantEncounter, MerchantInventoryItem, MerchantTransaction
from .serializers import (
    MerchantEncounterSerializer,
    MerchantInventoryItemSerializer,
    MerchantTransactionSerializer,
    PurchaseItemSerializer
)
from campaigns.models import CampaignCharacter


class MerchantViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing merchants.
    
    Merchants appear in campaigns and offer items based on gauntlet depth.
    """
    queryset = MerchantEncounter.objects.all().prefetch_related('inventory', 'inventory__item')
    serializer_class = MerchantEncounterSerializer
    
    def get_queryset(self):
        """Filter merchants by campaign if specified"""
        queryset = super().get_queryset()
        
        campaign_id = self.request.query_params.get('campaign')
        if campaign_id:
            queryset = queryset.filter(campaign_id=campaign_id)
        
        return queryset
    
    @action(detail=True, methods=['get'])
    def inventory(self, request, pk=None):
        """
        Get merchant's inventory.
        Optionally filter to show only available items.
        """
        merchant = self.get_object()
        available_only = request.query_params.get('available_only', 'false').lower() == 'true'
        
        if available_only:
            inventory = merchant.inventory.filter(is_sold=False)
        else:
            inventory = merchant.inventory.all()
        
        serializer = MerchantInventoryItemSerializer(inventory, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def purchase(self, request, pk=None):
        """
        Purchase an item from the merchant.
        
        Request body:
        {
            "inventory_item_id": 5,
            "campaign_character_id": 3
        }
        """
        merchant = self.get_object()
        serializer = PurchaseItemSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        inventory_item_id = serializer.validated_data['inventory_item_id']
        campaign_character_id = serializer.validated_data['campaign_character_id']
        
        try:
            # Get inventory item
            inventory_item = MerchantInventoryItem.objects.get(
                id=inventory_item_id,
                merchant=merchant
            )
            
            # Get campaign character
            campaign_character = CampaignCharacter.objects.get(id=campaign_character_id)
            
            # Verify character is in the same campaign
            if campaign_character.campaign != merchant.campaign:
                return Response(
                    {'error': 'Character is not in this campaign'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Check if item is already sold
            if inventory_item.is_sold:
                return Response(
                    {'error': 'Item already sold'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Check if character can afford it
            if campaign_character.gold < inventory_item.price:
                return Response(
                    {
                        'error': 'Not enough gold',
                        'required': inventory_item.price,
                        'available': campaign_character.gold,
                        'shortfall': inventory_item.price - campaign_character.gold
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Perform the purchase in a transaction
            with transaction.atomic():
                # Sell the item
                success = inventory_item.sell_to(campaign_character)
                
                if not success:
                    return Response(
                        {'error': 'Purchase failed'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Create transaction record
                merchant_transaction = MerchantTransaction.objects.create(
                    merchant=merchant,
                    campaign_character=campaign_character,
                    inventory_item=inventory_item,
                    item_name=inventory_item.item.name,
                    price=inventory_item.price
                )
            
            return Response({
                'message': 'Purchase successful',
                'item': inventory_item.item.name,
                'price': inventory_item.price,
                'gold_remaining': campaign_character.gold,
                'transaction_id': merchant_transaction.id
            }, status=status.HTTP_200_OK)
            
        except MerchantInventoryItem.DoesNotExist:
            return Response(
                {'error': 'Inventory item not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except CampaignCharacter.DoesNotExist:
            return Response(
                {'error': 'Campaign character not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def transactions(self, request, pk=None):
        """Get all transactions for this merchant"""
        merchant = self.get_object()
        transactions = merchant.transactions.all()
        serializer = MerchantTransactionSerializer(transactions, many=True)
        return Response(serializer.data)
