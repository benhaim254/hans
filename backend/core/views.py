from django.shortcuts import render

from .models import User


def index(request):
    users = User.objects.all()
    context = {"users": users}
    return render(request, "core/index.html", context)
