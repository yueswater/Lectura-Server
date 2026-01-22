from django.db import models
from django.utils.translation import gettext_lazy as _


class SectionLevel(models.TextChoices):
    SECTION = "section", _("Section (H2)")
    SUBSECTION = "subsection", _("Subsection (H3)")
    SUBSUBSECTION = "subsubsection", _("Subsubsection (H4)")
