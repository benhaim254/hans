from django.shortcuts import render
from .models import Appointment
from users.models import User
# Create your views here.

def index(request):
    appointments = Appointment.objects.all()
    context = {'appointments': appointments}
    return render(request, 'appointments/index.html', context)