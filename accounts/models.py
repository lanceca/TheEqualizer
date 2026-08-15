from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):

    class Role(models.TextChoices):
        SUPER_ADMIN = "SUPER_ADMIN", "Super Admin"
        ADMIN = "ADMIN", "Admin"
        ADVISER = "ADVISER", "Adviser"
        EIC = "EIC", "Editor in Chief"
        EDITOR = "EDITOR", "Editor"
        STAFF = "STAFF", "Staff"

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
    )

    def __str__(self):
        return self.username