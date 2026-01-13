from django.db import models
from django.utils import timezone
from campaigns.models import Campaign, CampaignCharacter
from items.models import Item
import random


class MerchantEncounter(models.Model):
    """
    Merchant discovered during a campaign.
    Merchants appear randomly and offer items based on encounter depth (gauntlet progress).
    """
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='merchants')
    encounter_number = models.IntegerField(help_text="Depth in the gauntlet when discovered")
    discovered_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True, help_text="Whether merchant is still available for trading")
    merchant_name = models.CharField(max_length=100, help_text="Randomly generated merchant name")
    
    class Meta:
        ordering = ['encounter_number', '-discovered_at']
        unique_together = ['campaign', 'encounter_number']
    
    def __str__(self):
        return f"{self.merchant_name} (Campaign: {self.campaign.name}, Encounter {self.encounter_number})"
    
    def generate_inventory(self, count=5):
        """
        Generate random inventory for this merchant based on encounter depth.
        Uses rarity-based weighted random selection.
        """
        from .rarity_weights import select_random_items
        
        # Get randomly selected items based on depth and rarity weights
        selected_items = select_random_items(self.encounter_number, count)
        
        # Create inventory items
        for item in selected_items:
            # Calculate price based on item rarity and base value
            price = self._calculate_price(item)
            
            MerchantInventoryItem.objects.create(
                merchant=self,
                item=item,
                price=price
            )
    
    def _calculate_price(self, item):
        """Calculate item price with some randomization"""
        base_price = item.value if hasattr(item, 'value') else 100
        
        # Add 0-20% variation
        variation = random.uniform(0.8, 1.2)
        return int(base_price * variation)
    
    def get_available_items(self):
        """Get unsold items from inventory"""
        return self.inventory.filter(is_sold=False)


class MerchantInventoryItem(models.Model):
    """
    Individual item in a merchant's inventory.
    """
    merchant = models.ForeignKey(MerchantEncounter, on_delete=models.CASCADE, related_name='inventory')
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1, help_text="Number of this item available")
    price = models.IntegerField(help_text="Price in gold pieces (GP)")
    is_sold = models.BooleanField(default=False)
    purchased_by = models.ForeignKey(
        CampaignCharacter,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='purchased_items'
    )
    purchased_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['is_sold', '-price']
    
    def __str__(self):
        status = "Sold" if self.is_sold else "Available"
        return f"{self.item.name} - {self.price} GP ({status})"
    
    def sell_to(self, campaign_character):
        """
        Sell this item to a character.
        Returns True if successful, False if character can't afford it.
        """
        if self.is_sold:
            raise ValueError("Item already sold")
        
        if campaign_character.gold < self.price:
            return False
        
        # Deduct gold
        campaign_character.gold -= self.price
        campaign_character.save()
        
        # Mark as sold
        self.is_sold = True
        self.purchased_by = campaign_character
        self.purchased_at = timezone.now()
        self.save()
        
        # Add to character inventory (if inventory tracking exists)
        try:
            from characters.models import CharacterInventoryItem
            CharacterInventoryItem.objects.create(
                character=campaign_character.character,
                item=self.item,
                quantity=self.quantity,
                equipped=False
            )
        except ImportError:
            pass  # Inventory tracking not available
        
        return True


class MerchantTransaction(models.Model):
    """
    Record of a merchant transaction for auditing and history.
    """
    merchant = models.ForeignKey(MerchantEncounter, on_delete=models.CASCADE, related_name='transactions')
    campaign_character = models.ForeignKey(CampaignCharacter, on_delete=models.CASCADE, related_name='transactions')
    inventory_item = models.ForeignKey(MerchantInventoryItem, on_delete=models.CASCADE)
    item_name = models.CharField(max_length=100, help_text="Item name at time of purchase")
    price = models.IntegerField(help_text="Price paid in gold")
    purchased_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-purchased_at']
    
    def __str__(self):
        return f"{self.campaign_character.character.name} bought {self.item_name} for {self.price} GP"
