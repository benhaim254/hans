from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from users.decorators import role_required
from users.models import ROLE_DOCTOR, ROLE_PATIENT

from .forms import AppointmentForm, CancelAppointmentForm
from .models import Appointment


@role_required(ROLE_PATIENT)
def patient_dashboard(request):
    if request.method == 'POST':
        form = AppointmentForm(request.POST)
        form.instance.patient = request.user
        if form.is_valid():
            form.save()
            messages.success(request, 'Appointment requested. The doctor will confirm it shortly.')
            return redirect('patient_dashboard')
    else:
        form = AppointmentForm()

    appointments = (Appointment.objects
                    .filter(patient=request.user)
                    .select_related('doctor'))
    return render(request, 'appointments/patient_dashboard.html', {
        'appointments': appointments,
        'form': form,
    })


@role_required(ROLE_DOCTOR)
def doctor_dashboard(request):
    appointments = (Appointment.objects
                    .filter(doctor=request.user)
                    .select_related('patient'))
    return render(request, 'appointments/doctor_dashboard.html', {
        'appointments': appointments,
    })


@require_POST
@role_required(ROLE_DOCTOR)
def confirm_appointment(request, appointment_id):
    appointment = get_object_or_404(Appointment, appointment_id=appointment_id, doctor=request.user)
    try:
        appointment.confirm()
        messages.success(request, 'Appointment confirmed.')
    except ValidationError as error:
        messages.error(request, error.messages[0])
    return redirect('doctor_dashboard')


@require_POST
@role_required(ROLE_PATIENT)
def cancel_appointment(request, appointment_id):
    appointment = get_object_or_404(Appointment, appointment_id=appointment_id, patient=request.user)
    form = CancelAppointmentForm(request.POST)
    if not form.is_valid():
        messages.error(request, 'Please give a reason for canceling.')
        return redirect('patient_dashboard')
    try:
        appointment.cancel(form.cleaned_data['cancellation_reason'])
        messages.success(request, 'Appointment canceled.')
    except ValidationError as error:
        messages.error(request, error.messages[0])
    return redirect('patient_dashboard')
