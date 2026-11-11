from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from users.decorators import role_required
from users.models import ROLE_DOCTOR, ROLE_PATIENT

from .forms import AppointmentForm, AvailabilityForm, CancelAppointmentForm
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
        'has_working_hours': request.user.working_hours.exists(),
    })


@role_required(ROLE_DOCTOR)
def availability(request):
    form = AvailabilityForm(request.POST or None, doctor=request.user)
    if form.is_valid():
        form.save()
        messages.success(request, 'Availability saved.')
        return redirect('availability')
    return render(request, 'appointments/availability.html', {'form': form})


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


def _doctor_transition(request, appointment_id, change, done_message):
    appointment = get_object_or_404(Appointment, appointment_id=appointment_id, doctor=request.user)
    try:
        change(appointment)
        messages.success(request, done_message)
    except ValidationError as error:
        messages.error(request, error.messages[0])
    return redirect('doctor_dashboard')


@require_POST
@role_required(ROLE_DOCTOR)
def complete_appointment(request, appointment_id):
    return _doctor_transition(request, appointment_id, Appointment.complete, 'Appointment marked as completed.')


@require_POST
@role_required(ROLE_DOCTOR)
def no_show_appointment(request, appointment_id):
    return _doctor_transition(request, appointment_id, Appointment.mark_no_show, 'Appointment marked as a no-show.')


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
