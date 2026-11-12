import uuid
from django.db import models
from django.utils import timezone


class OrganizationModel(models.Model):
    class OrganizationType(models.IntegerChoices):
        SCHOOL = 1
        COLLEGE = 2
        PRIVATE_TUITION = 3
        PRIVATE_SECTOR = 4

    id = models.UUIDField(primary_key=True, editable=False, default=uuid.uuid4)
    name = models.CharField(max_length=255)
    short_name = models.CharField(max_length=100, unique=True)
    description = models.CharField(max_length=1000, null=True, blank=True)
    type = models.SmallIntegerField(choices=OrganizationType)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(null=True, blank=True)
    created_by = models.CharField(max_length=100)
    updated_by = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        db_table = "organizations"
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["type"]),
            models.Index(
                fields=["short_name"],
                condition=models.Q(is_deleted=False),
                name="idx_org_short_name",
            ),
        ]
        constraints = []

    Meta.constraints = [
        models.CheckConstraint(
            condition=models.Q(type__in=OrganizationType.values),
            name="ck_organization_type_valid",
        ),
    ]

    def save(self, *args, **kwargs):
        if not self.pk:
            self.created_at = timezone.now()
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)
