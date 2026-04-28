from django.contrib.auth.models import AbstractUser
from django.db import models


class Merchant(AbstractUser):
    """Custom user model for merchants."""

    email = models.EmailField(unique=True)
    business_name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    # Use email instead of username for authentication
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'business_name']

    class Meta:
        db_table = 'merchants'

    def __str__(self):
        return f"{self.business_name} ({self.email})"
