from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from shared.infrastructure.reference_cache import invalidate_reference
from workforce.infrastructure.models import Department, Employee, Position, Role


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


@receiver(post_save, sender=Department)
@receiver(post_delete, sender=Department)
@receiver(post_save, sender=Position)
@receiver(post_delete, sender=Position)
@receiver(post_save, sender=Role)
@receiver(post_delete, sender=Role)
def invalidate_reference_list(sender, using: str, **kwargs: object) -> None:
    resources = {Department: "departments", Position: "positions", Role: "roles"}
    invalidate_reference(f"workforce:{resources[sender]}", using=using)


@receiver(post_delete, sender=Employee)
def invalidate_deleted_department_head(using: str, **kwargs: object) -> None:
    # Django SET_NULL can update Department.head without a Department post_save signal.
    invalidate_reference("workforce:departments", using=using)
