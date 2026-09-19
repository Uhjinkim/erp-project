from django.db.models.signals import post_save
from django.dispatch import receiver

from workforce.infrastructure.models import Employee


@receiver(post_save, sender=Employee)
def deactivate_account_for_inactive_employee(
    sender: type[Employee],
    instance: Employee,
    **kwargs: object,
) -> None:
    if instance.is_active_employee:
        return

    from accounts.models import User

    User.objects.filter(employee=instance, is_active=True).update(is_active=False)
