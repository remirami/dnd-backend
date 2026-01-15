import uuid
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta


class CharacterBuilderSession(models.Model):
    """
    Temporary storage for in-progress character builds
    
    Stores wizard progress and auto-expires after 24 hours
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='builder_sessions')
    
    current_step = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(7)],
        help_text="Current step in the character creation wizard (1-7)"
    )
    
    # JSON structure:
    # {
    #   "method": "point_buy" | "standard_array" | "manual",
    #   "base_scores": {"str": 15, "dex": 14, "con": 13, "int": 12, "wis": 10, "cha": 8},
    #   "race_id": 2,
    #   "final_scores": {"str": 16, "dex": 14, ...},  # After racial bonuses
    #   "class_id": 3,
    #   "subclass": "champion",
    #   "background_id": 1,
    #   "skills": ["Acrobatics", "Perception"],
    #   "equipment_ids": [1, 5, 12],
    #   "starting_gold": 50
    # }
    data = models.JSONField(default=dict)
    
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    
    class Meta:
        indexes = [
            models.Index(fields=['user', '-created_at'], name='builder_user_created_idx'),
            models.Index(fields=['expires_at'], name='builder_expires_idx'),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Builder Session {self.id} - Step {self.current_step} ({self.user.username})"
    
    def save(self, *args, **kwargs):
        # Auto-set expiry if not set
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=24)
        super().save(*args, **kwargs)
    
    def is_expired(self):
        """Check if session has expired"""
        return timezone.now() > self.expires_at
    
    def extend_session(self, hours=24):
        """Extend session expiry"""
        self.expires_at = timezone.now() + timedelta(hours=hours)
        self.save()
