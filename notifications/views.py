from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def notification_list(request):
    notifications = list(request.user.notifications.all()[:50])
    # Opening the page counts as reading what is shown on it, not older unread ones beyond the cap.
    request.user.notifications.filter(pk__in=[n.pk for n in notifications], is_read=False).update(is_read=True)
    return render(request, 'notifications/list.html', {'notifications': notifications})
