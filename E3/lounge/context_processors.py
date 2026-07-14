from .models import Notification


def notifications(request):
    if not request.user.is_authenticated:
        return {"unread_notifications_count": 0, "recent_notifications": []}
    unread = Notification.objects.filter(user=request.user, is_read=False)
    return {
        "unread_notifications_count": unread.count(),
        "recent_notifications": Notification.objects.filter(user=request.user).order_by("-created_at")[:5],
    }
