from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from users.decorators import role_required
from users.models import ROLE_DOCTOR, ROLE_PATIENT

from .forms import AppointmentForm, AvailabilityForm, CancelAppointmentForm, NewTimeForm, TimeOffForm, VisitNotesForm
from .models import CANCELABLE_STATUSES, DOUBLE_BOOKED_MESSAGE, STATUS_COMPLETED, STATUS_PENDING, Appointment, TimeOff, lock_doctor_schedule


@role_required(ROLE_PATIENT)
def patient_dashboard(request):
    if request.method == 'POST':
        form = AppointmentForm(request.POST)
        form.instance.patient = request.user
        if form.is_valid():
            try:
                with transaction.atomic():
                    form.save()
            except ValidationError as error:  # the slot was taken or blocked after our form check ran
                form.add_error(None, error.messages)
            except IntegrityError:
                form.add_error(None, DOUBLE_BOOKED_MESSAGE)
            else:
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
    # shortcut: loads every appointment the doctor has ever had; paginate Past once lists get long.
    appointments = list(Appointment.objects
                        .filter(doctor=request.user)
                        .select_related('patient__patientprofile')
                        .order_by('appointment_date', 'appointment_time'))
    today = timezone.localdate()
    sections = [
        ('Today', 'bi-calendar-day', [a for a in appointments if a.appointment_date == today],
         'Nothing booked for today.'),
        ('Upcoming', 'bi-calendar-week', [a for a in appointments if a.appointment_date > today],
         'No upcoming appointments.'),
        ('Past', 'bi-clock-history', [a for a in reversed(appointments) if a.appointment_date < today],
         'No past appointments yet.'),
    ]
    return render(request, 'appointments/doctor_dashboard.html', {
        'sections': sections,
        'has_working_hours': request.user.working_hours.exists(),
    })


@role_required(ROLE_DOCTOR)
def availability(request):
    form = AvailabilityForm(request.POST or None, doctor=request.user)
    if form.is_valid():
        form.save()
        messages.success(request, 'Availability saved.')
        return redirect('availability')
    return _render_availability(request, form, TimeOffForm())


def _render_availability(request, form, time_off_form):
    return render(request, 'appointments/availability.html', {
        'form': form,
        'time_off_form': time_off_form,
        'time_off': request.user.time_off.filter(end_date__gte=timezone.localdate()),
    })


@require_POST
@role_required(ROLE_DOCTOR)
def add_time_off(request):
    time_off_form = TimeOffForm(request.POST, instance=TimeOff(doctor=request.user))
    if not time_off_form.is_valid():
        return _render_availability(request, AvailabilityForm(doctor=request.user), time_off_form)
    # Under the doctor's lock, so a booking being saved right now is either counted below or refused.
    with transaction.atomic():
        lock_doctor_schedule(request.user.pk)
        time_off = time_off_form.save()
        clashes = Appointment.objects.filter(
            doctor=request.user, status__in=CANCELABLE_STATUSES,
            appointment_date__range=(time_off.start_date, time_off.end_date)).count()
    messages.success(request, 'Time off added. No new bookings will be accepted on those days.')
    if clashes:
        messages.warning(request, f'You already have {clashes} appointment(s) during this time off. '
                                  'Decline or move them from your schedule.')
    return redirect('availability')


@require_POST
@role_required(ROLE_DOCTOR)
def delete_time_off(request, pk):
    get_object_or_404(TimeOff, pk=pk, doctor=request.user).delete()
    messages.success(request, 'Time off removed.')
    return redirect('availability')


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


@role_required(ROLE_DOCTOR)
def visit_notes(request, appointment_id):
    """Private notes on a completed appointment; only the treating doctor can read or edit them."""
    appointment = get_object_or_404(Appointment.objects.select_related('patient'), appointment_id=appointment_id,
                                    doctor=request.user, status=STATUS_COMPLETED)
    form = VisitNotesForm(request.POST or None, instance=appointment)
    if form.is_valid():
        form.save()
        messages.success(request, 'Visit notes saved.')
        return redirect('doctor_dashboard')
    return render(request, 'appointments/visit_notes.html', {'appointment': appointment, 'form': form})


@role_required(ROLE_DOCTOR)
def respond_to_request(request, appointment_id):
    """Doctor declines a pending request with a reason, or proposes a different free time."""
    appointment = get_object_or_404(Appointment.objects.select_related('patient'), appointment_id=appointment_id,
                                    doctor=request.user, status=STATUS_PENDING)
    decline_form = CancelAppointmentForm(request.POST if request.POST.get('action') == 'decline' else None)
    propose_form = NewTimeForm(request.POST if request.POST.get('action') == 'propose' else None)
    if decline_form.is_valid():
        try:
            appointment.decline(decline_form.cleaned_data['cancellation_reason'])
            messages.success(request, 'Request declined. The patient has been told why.')
        except ValidationError as error:  # e.g. the patient cancelled after this page loaded
            messages.error(request, error.messages[0])
        return redirect('doctor_dashboard')
    if propose_form.is_valid() and propose_form.apply(appointment.propose):
        messages.success(request, 'New time proposed. The patient can accept or decline it.')
        return redirect('doctor_dashboard')
    return render(request, 'appointments/respond.html', {
        'appointment': appointment, 'decline_form': decline_form, 'propose_form': propose_form})


@role_required(ROLE_PATIENT)
def reschedule_appointment(request, appointment_id):
    appointment = get_object_or_404(Appointment.objects.select_related('doctor'), appointment_id=appointment_id,
                                    patient=request.user, status__in=CANCELABLE_STATUSES)
    form = NewTimeForm(request.POST or None)
    if form.is_valid() and form.apply(appointment.reschedule):
        messages.success(request, 'Appointment moved. The doctor will confirm the new time.')
        return redirect('patient_dashboard')
    return render(request, 'appointments/reschedule.html', {'appointment': appointment, 'form': form})


@require_POST
@role_required(ROLE_PATIENT)
def accept_proposal(request, appointment_id):
    appointment = get_object_or_404(Appointment, appointment_id=appointment_id, patient=request.user)
    try:
        appointment.accept_proposal()
        messages.success(request, 'New time accepted. Your appointment is scheduled.')
    except ValidationError as error:
        messages.error(request, error.messages[0])
    return redirect('patient_dashboard')


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
