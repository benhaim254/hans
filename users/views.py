from django.shortcuts import render
from .models import User
# Create your views here.

def index(request):
    users = User.objects.filter(role__in=['patient', 'doctor'])
    context = {'users': users}
    return render(request, 'users/index.html', context)