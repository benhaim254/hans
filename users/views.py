from django.shortcuts import render
from .models import User


def index(request):
    """
    View to display all users in the system.
    This is a simple view that retrieves all users and renders them in a template.
    """
    
    users = User.objects.filter(
        role__in=[User.ROLE_PATIENT, User.ROLE_DOCTOR
                  ])
    context = {'users': users}
    return render(request, 'users/index.html', context)