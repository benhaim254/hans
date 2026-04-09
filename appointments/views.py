from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Appointment
from users.models import User
from users.views import redirect_by_role

@login_required
def patient_dashboard(request):
    appointments = Appointment.objects.filter(
        patient=request.user
    ).order_by('-appointment_date')
    return render(request, 'appointments/patient_dashboard.html', {
        'appointments': appointments,
    })

@login_required
def doctor_dashboard(request):
    appointments = Appointment.objects.filter(
        doctor=request.user
    ).order_by('-appointment_date')
    return render(request, 'appointments/doctor_dashboard.html', {
        'appointments': appointments,
    })

@login_required
def confirm_appointment(request, appointment_id):
    appointment = get_object_or_404(
        Appointment,
        id=appointment_id,
        doctor=request.user
    )
    if request.method == 'POST':
        appointment.status = 'scheduled'
        appointment.save()
    return redirect('doctor_dashboard')

def index(request):
    appointments = Appointment.objects.all()
    context = {'appointments': appointments}
    return render(request, 'appointments/index.html', context)