from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from shared.infrastructure.reference_cache import invalidate_reference
from vacation.infrastructure.models import LeaveTypeModel


@receiver(post_save, sender=LeaveTypeModel)
@receiver(post_delete, sender=LeaveTypeModel)
def invalidate_type_list(using: str, **kwargs: object) -> None:
    invalidate_reference("vacation:types", using=using)
