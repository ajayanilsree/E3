from django.contrib.auth.models import Group, User
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import MemberProfile
from .roles import CUSTOMER


@receiver(post_save, sender=User)
def create_customer_profile(sender, instance, created, **kwargs):
    if not created or instance.is_staff:
        return
    customer_group, _ = Group.objects.get_or_create(name=CUSTOMER)
    if not instance.groups.exists():
        instance.groups.add(customer_group)
    MemberProfile.objects.get_or_create(user=instance)
