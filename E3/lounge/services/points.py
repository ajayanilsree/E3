from decimal import Decimal, ROUND_FLOOR
from typing import Optional

from django.contrib.auth.models import User

from lounge.models import MemberProfile, PointTransaction

POINTS_PER_100_RUPEES = 10


def calculate_points(amount: Decimal) -> int:
    spend_blocks = (amount / Decimal("100")).to_integral_value(rounding=ROUND_FLOOR)
    return int(spend_blocks) * POINTS_PER_100_RUPEES


def award_points(*, member: Optional[MemberProfile], amount: Decimal, reason: str, created_by: Optional[User] = None) -> Optional[PointTransaction]:
    if not member:
        return None
    points = calculate_points(amount)
    if points <= 0:
        return None
    return PointTransaction.objects.create(member=member, points=points, reason=reason, created_by=created_by)
