from django.db import models
from django.utils import timezone
import uuid

class ReminderModel(models.Model):
    id = models.UUIDField(primary_key=True, editable=False, default=uuid.uuid4)
    post_id = models.ForeignKey()
    is_reminder_set = models.BooleanField(default=False, null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(null=True, blank=True)
    created_by = models.CharField(max_length=100)
    
    
    class Meta:
        db_table = 'reminders'
        indexes = [
            models.Index(fields=['id']),
        ]
    
    
    def save(self, *args, **kwards):
        if not self.pk:
            self.created_at = timezone.now()
        self.updated_at = timezone.now()
        super().save(*args, **kwards)
