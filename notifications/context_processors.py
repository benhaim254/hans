def unread_notifications(request):
    """Unread count for the bell in the navbar."""
    if not request.user.is_authenticated:
        return {}
    return {'unread_notifications': request.user.notifications.filter(is_read=False).count()}
