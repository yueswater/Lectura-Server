from django.db import models
from django.utils.translation import gettext_lazy as _


class UserRole(models.TextChoices):
    SUPERUSER = "SUPERUSER", "Superuser"
    ADMIN = "ADMIN", "Administrator"
    EDITOR = "EDITOR", "Editor"
    VIEWER = "VIEWER", "Viewer"


class Tier(models.TextChoices):
    BETA = "BETA", _("Beta Tester")
    FREE = "FREE", _("Free")
    PRO = "PRO", _("Professional")
    ENTERPRISE = "ENTERPRISE", _("Enterprise")

    @property
    def storage_limit(self):
        limits = {
            self.BETA: 500 * 1024 * 1024,
            # self.FREE: 50 * 1024 * 1024,
            self.FREE: int(0.1 * 1024 * 1024),
            self.PRO: 2 * 1024 * 1024 * 1024,
            self.ENTERPRISE: 50 * 1024 * 1024 * 1024,
        }
        return limits.get(self, limits[self.FREE])
