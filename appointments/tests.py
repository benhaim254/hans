from datetime import time, timedelta
from io import StringIO

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from users.models import ROLE_DOCTOR, ROLE_PATIENT, User
from users.tests import make_verified_doctor

from .models import (STATUS_CANCELED, STATUS_COMPLETED, STATUS_NO_SHOW, STATUS_PENDING, STATUS_SCHEDULED,
                     Appointment, WorkingHours, available_slots)

TOMORROW = timezone.localdate() + timedelta(days=1)


def set_hours(doctor, start=time(8, 0), end=time(17, 0), days=range(7), length=None):
    """Give a doctor the same working range on the given weekdays (every day by default)."""
    for day in days:
        WorkingHours.objects.update_or_create(doctor=doctor, weekday=day,
                                              defaults={'start_time': start, 'end_time': end})
    if length:
        doctor.doctorprofile.appointment_length = length
        doctor.doctorprofile.save()


class AppointmentTestCase(TestCase):
    def setUp(self):
        self.patient = User.objects.create_user('pat', password='x', role=ROLE_PATIENT)
        self.other_patient = User.objects.create_user('pat2', password='x', role=ROLE_PATIENT)
        self.doctor = make_verified_doctor('doc')
        self.other_doctor = make_verified_doctor('doc2')
        set_hours(self.doctor)
        set_hours(self.other_doctor)

    def book(self, patient=None, status=STATUS_PENDING, **overrides):
        fields = dict(patient=patient or self.patient, doctor=self.doctor,
                      appointment_date=TOMORROW, appointment_time=time(9, 0), status=status)
        fields.update(overrides)
        return Appointment.objects.create(**fields)


class DoubleBookingTests(AppointmentTestCase):
    def test_database_blocks_same_doctor_slot(self):
        self.book()
        with self.assertRaises(IntegrityError):
            self.book(patient=self.other_patient)

    def test_canceled_appointment_frees_slot(self):
        self.book(status=STATUS_CANCELED)
        self.book(patient=self.other_patient)  # no error


class PatientWebTests(AppointmentTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.patient)
        self.url = reverse('patient_dashboard')

    def post_booking(self, **overrides):
        data = {'doctor': self.doctor.pk, 'appointment_date': TOMORROW, 'appointment_time': '09:00', 'reason': 'Checkup'}
        data.update(overrides)
        return self.client.post(self.url, data)

    def test_patient_can_book(self):
        response = self.post_booking()
        self.assertRedirects(response, self.url)
        appointment = Appointment.objects.get()
        self.assertEqual(appointment.patient, self.patient)
        self.assertEqual(appointment.status, STATUS_PENDING)

    def test_double_booking_shows_form_error(self):
        self.book(patient=self.other_patient)
        response = self.post_booking()
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'already booked')
        self.assertEqual(Appointment.objects.count(), 1)

    def test_unverified_doctor_cannot_be_booked(self):
        unverified = User.objects.create_user('nolicense', password='x', role=ROLE_DOCTOR)
        response = self.post_booking(doctor=unverified.pk)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Appointment.objects.exists())

    def test_past_date_rejected(self):
        response = self.post_booking(appointment_date=timezone.localdate() - timedelta(days=1))
        self.assertContains(response, 'in the past')
        self.assertFalse(Appointment.objects.exists())

    def test_patient_can_cancel_own_appointment(self):
        appointment = self.book()
        self.client.post(reverse('cancel_appointment', args=[appointment.appointment_id]),
                         {'cancellation_reason': 'Travelling'})
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, STATUS_CANCELED)
        self.assertEqual(appointment.cancellation_reason, 'Travelling')

    def test_patient_cannot_cancel_someone_elses_appointment(self):
        appointment = self.book(patient=self.other_patient)
        response = self.client.post(reverse('cancel_appointment', args=[appointment.appointment_id]),
                                    {'cancellation_reason': 'Nope'})
        self.assertEqual(response.status_code, 404)

    def test_patient_cannot_open_doctor_dashboard(self):
        self.assertEqual(self.client.get(reverse('doctor_dashboard')).status_code, 403)


class DoctorWebTests(AppointmentTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.doctor)

    def test_doctor_can_confirm_own_appointment(self):
        appointment = self.book()
        self.client.post(reverse('confirm_appointment', args=[appointment.appointment_id]))
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, STATUS_SCHEDULED)

    def test_doctor_cannot_confirm_other_doctors_appointment(self):
        appointment = self.book(doctor=self.other_doctor)
        response = self.client.post(reverse('confirm_appointment', args=[appointment.appointment_id]))
        self.assertEqual(response.status_code, 404)

    def test_confirm_requires_post(self):
        appointment = self.book()
        response = self.client.get(reverse('confirm_appointment', args=[appointment.appointment_id]))
        self.assertEqual(response.status_code, 405)

    def test_doctor_cannot_open_patient_dashboard(self):
        self.assertEqual(self.client.get(reverse('patient_dashboard')).status_code, 403)


class AppointmentApiTests(AppointmentTestCase):
    list_url = reverse('appointment-list')

    def setUp(self):
        super().setUp()
        self.api = APIClient()

    def as_user(self, user):
        self.api.force_authenticate(user)
        return self.api

    def test_requires_authentication(self):
        self.assertEqual(self.api.get(self.list_url).status_code, 401)

    def test_patient_books_via_api(self):
        response = self.as_user(self.patient).post(self.list_url, {
            'doctor': self.doctor.pk, 'appointment_date': TOMORROW, 'appointment_time': '10:00'})
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(Appointment.objects.get().patient, self.patient)

    def test_api_rejects_double_booking(self):
        self.book(patient=self.other_patient)
        response = self.as_user(self.patient).post(self.list_url, {
            'doctor': self.doctor.pk, 'appointment_date': TOMORROW, 'appointment_time': '09:00'})
        self.assertEqual(response.status_code, 400)

    def test_api_rejects_non_doctor_as_doctor(self):
        response = self.as_user(self.patient).post(self.list_url, {
            'doctor': self.other_patient.pk, 'appointment_date': TOMORROW, 'appointment_time': '10:00'})
        self.assertEqual(response.status_code, 400)

    def test_doctor_cannot_book(self):
        response = self.as_user(self.doctor).post(self.list_url, {
            'doctor': self.doctor.pk, 'appointment_date': TOMORROW, 'appointment_time': '10:00'})
        self.assertEqual(response.status_code, 403)

    def test_list_is_scoped_to_user(self):
        mine = self.book()
        self.book(patient=self.other_patient, doctor=self.other_doctor)
        response = self.as_user(self.patient).get(self.list_url)
        self.assertEqual([a['appointment_id'] for a in response.data], [str(mine.appointment_id)])

    def test_doctor_confirms_via_api(self):
        appointment = self.book()
        url = reverse('appointment-confirm', args=[appointment.appointment_id])
        response = self.as_user(self.doctor).post(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], STATUS_SCHEDULED)
        # Confirming twice is a bad request, not a crash.
        self.assertEqual(self.as_user(self.doctor).post(url).status_code, 400)

    def test_patient_cancels_via_api(self):
        appointment = self.book()
        url = reverse('appointment-cancel', args=[appointment.appointment_id])
        self.assertEqual(self.as_user(self.patient).post(url, {}).status_code, 400)
        response = self.as_user(self.patient).post(url, {'cancellation_reason': 'Sick'})
        self.assertEqual(response.data['status'], STATUS_CANCELED)

    def test_patient_cannot_confirm(self):
        appointment = self.book()
        url = reverse('appointment-confirm', args=[appointment.appointment_id])
        self.assertEqual(self.as_user(self.patient).post(url).status_code, 403)


class SeedDemoTests(TestCase):
    def test_seed_is_idempotent(self):
        call_command('seed_demo', stdout=StringIO())
        call_command('seed_demo', stdout=StringIO())
        self.assertEqual(User.objects.verified_doctors().count(), 3)
        self.assertEqual(Appointment.objects.count(), 4)
        past = Appointment.objects.get(status=STATUS_SCHEDULED)
        self.assertTrue(past.has_started)


class WorkingHoursBookingTests(AppointmentTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.patient)

    def post_booking(self, at, day=TOMORROW):
        return self.client.post(reverse('patient_dashboard'), {
            'doctor': self.doctor.pk, 'appointment_date': day, 'appointment_time': at})

    def test_booking_takes_doctor_length_and_keeps_it(self):
        set_hours(self.doctor, length=45)
        self.post_booking('09:00')
        appointment = Appointment.objects.get()
        self.assertEqual(appointment.duration_minutes, 45)
        self.assertEqual(appointment.end_time, time(9, 45))
        set_hours(self.doctor, length=60)
        appointment.refresh_from_db()
        self.assertEqual(appointment.duration_minutes, 45)

    def test_day_off_rejected(self):
        WorkingHours.objects.filter(doctor=self.doctor, weekday=TOMORROW.weekday()).delete()
        response = self.post_booking('09:00')
        self.assertContains(response, "doesn&#x27;t work on that day")
        self.assertFalse(Appointment.objects.exists())

    def test_must_fit_inside_hours(self):
        set_hours(self.doctor, length=60)
        self.assertContains(self.post_booking('07:30'), 'must fit between 08:00 and 17:00')
        self.assertContains(self.post_booking('16:30'), 'must fit between 08:00 and 17:00')
        self.assertFalse(Appointment.objects.exists())
        self.post_booking('16:00')
        self.assertTrue(Appointment.objects.exists())

    def test_overlap_with_longer_appointment_rejected(self):
        set_hours(self.doctor, length=60)
        self.book(patient=self.other_patient)  # 09:00 to 10:00
        self.assertContains(self.post_booking('09:30'), 'already booked')
        self.assertContains(self.post_booking('08:30'), 'already booked')
        self.post_booking('10:00')
        self.assertEqual(Appointment.objects.count(), 2)


class AvailableSlotsTests(AppointmentTestCase):
    def test_slots_follow_hours_length_and_bookings(self):
        set_hours(self.doctor, start=time(9, 0), end=time(11, 0), length=30)
        self.book(appointment_time=time(9, 30))  # takes 09:30 to 10:00
        slots = [slot.strftime('%H:%M') for slot in available_slots(self.doctor, TOMORROW)]
        self.assertEqual(slots, ['09:00', '10:00', '10:15', '10:30'])

    def test_canceled_booking_frees_its_slots(self):
        set_hours(self.doctor, start=time(9, 0), end=time(10, 0), length=60)
        self.book(status=STATUS_CANCELED)
        self.assertEqual(available_slots(self.doctor, TOMORROW), [time(9, 0)])

    def test_no_slots_on_day_off_or_in_past(self):
        WorkingHours.objects.filter(doctor=self.doctor, weekday=TOMORROW.weekday()).delete()
        self.assertEqual(available_slots(self.doctor, TOMORROW), [])
        self.assertEqual(available_slots(self.doctor, timezone.localdate() - timedelta(days=1)), [])

    def test_slots_api_with_browser_session(self):
        set_hours(self.doctor, start=time(9, 0), end=time(10, 0), length=30)
        self.client.force_login(self.patient)
        url = reverse('doctor_slots', args=[self.doctor.pk])
        response = self.client.get(url, {'date': TOMORROW.isoformat()})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'date': TOMORROW.isoformat(), 'duration_minutes': 30,
                                           'slots': ['09:00', '09:15', '09:30']})
        self.assertEqual(self.client.get(url, {'date': '2026-02-30'}).status_code, 400)
        self.assertEqual(self.client.get(url).status_code, 400)

    def test_slots_api_rejects_unverified_doctor_and_anonymous(self):
        unverified = User.objects.create_user('nolicense', password='x', role=ROLE_DOCTOR)
        self.client.force_login(self.patient)
        self.assertEqual(self.client.get(reverse('doctor_slots', args=[unverified.pk]),
                                         {'date': TOMORROW.isoformat()}).status_code, 404)
        self.client.logout()
        self.assertEqual(self.client.get(reverse('doctor_slots', args=[self.doctor.pk]),
                                         {'date': TOMORROW.isoformat()}).status_code, 401)


class AvailabilityPageTests(AppointmentTestCase):
    url = reverse('availability')

    def form_data(self, **overrides):
        data = {'appointment_length': 45}
        for day in range(7):
            data.update({f'works_{day}': day < 5, f'start_{day}': '08:00', f'end_{day}': '16:00'})
        data = {key: value for key, value in data.items() if value is not False}
        data.update(overrides)
        return data

    def test_doctor_saves_hours_and_length(self):
        self.client.force_login(self.doctor)
        response = self.client.post(self.url, self.form_data())
        self.assertRedirects(response, self.url)
        self.assertEqual(list(self.doctor.working_hours.values_list('weekday', flat=True)), [0, 1, 2, 3, 4])
        self.assertEqual(self.doctor.working_hours.first().end_time, time(16, 0))
        self.doctor.doctorprofile.refresh_from_db()
        self.assertEqual(self.doctor.doctorprofile.appointment_length, 45)

    def test_end_before_start_rejected(self):
        self.client.force_login(self.doctor)
        response = self.client.post(self.url, self.form_data(end_0='07:00'))
        self.assertContains(response, 'Monday must end after it starts')
        self.assertEqual(self.doctor.working_hours.count(), 7)  # unchanged from setUp

    def test_length_below_30_rejected(self):
        self.client.force_login(self.doctor)
        response = self.client.post(self.url, self.form_data(appointment_length=15))
        self.assertEqual(response.status_code, 200)
        self.doctor.doctorprofile.refresh_from_db()
        self.assertEqual(self.doctor.doctorprofile.appointment_length, 30)

    def test_patient_cannot_open(self):
        self.client.force_login(self.patient)
        self.assertEqual(self.client.get(self.url).status_code, 403)


class CloseAppointmentTests(AppointmentTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.doctor)
        yesterday = timezone.localdate() - timedelta(days=1)
        self.past = self.book(status=STATUS_SCHEDULED, appointment_date=yesterday)

    def test_doctor_marks_completed(self):
        self.client.post(reverse('complete_appointment', args=[self.past.appointment_id]))
        self.past.refresh_from_db()
        self.assertEqual(self.past.status, STATUS_COMPLETED)

    def test_doctor_marks_no_show_and_patient_is_told(self):
        self.client.post(reverse('no_show_appointment', args=[self.past.appointment_id]))
        self.past.refresh_from_db()
        self.assertEqual(self.past.status, STATUS_NO_SHOW)
        self.assertIn('missing your appointment', self.patient.notifications.first().message)

    def test_cannot_close_before_it_starts(self):
        upcoming = self.book(status=STATUS_SCHEDULED, appointment_time=time(10, 0))
        self.client.post(reverse('complete_appointment', args=[upcoming.appointment_id]))
        upcoming.refresh_from_db()
        self.assertEqual(upcoming.status, STATUS_SCHEDULED)

    def test_cannot_close_pending_or_closed_twice(self):
        pending = self.book(appointment_date=self.past.appointment_date, appointment_time=time(10, 0))
        response = self.client.post(reverse('complete_appointment', args=[pending.appointment_id]), follow=True)
        self.assertContains(response, 'Only scheduled appointments can be closed')
        self.past.complete()
        with self.assertRaises(ValidationError):
            self.past.mark_no_show()

    def test_other_doctor_and_patient_cannot_close(self):
        self.client.force_login(self.other_doctor)
        self.assertEqual(self.client.post(reverse('complete_appointment', args=[self.past.appointment_id])).status_code, 404)
        self.client.force_login(self.patient)
        self.assertEqual(self.client.post(reverse('complete_appointment', args=[self.past.appointment_id])).status_code, 403)

    def test_api_complete_and_no_show(self):
        api = APIClient()
        api.force_authenticate(self.doctor)
        response = api.post(reverse('appointment-no-show', args=[self.past.appointment_id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], STATUS_NO_SHOW)
        self.assertEqual(api.post(reverse('appointment-complete', args=[self.past.appointment_id])).status_code, 400)
        api.force_authenticate(self.patient)
        self.assertEqual(api.post(reverse('appointment-complete', args=[self.past.appointment_id])).status_code, 403)


class PatientDetailsForDoctorTests(AppointmentTestCase):
    def test_doctor_sees_own_patients_details(self):
        profile = self.patient.patientprofile
        profile.allergies = 'Penicillin'
        profile.blood_group = 'O+'
        profile.save()
        self.book()
        self.client.force_login(self.doctor)
        response = self.client.get(reverse('doctor_dashboard'))
        self.assertContains(response, 'Penicillin')
        self.assertContains(response, 'O+')

    def test_other_doctor_sees_nothing(self):
        self.patient.patientprofile.allergies = 'Penicillin'
        self.patient.patientprofile.save()
        self.book()
        self.client.force_login(self.other_doctor)
        self.assertNotContains(self.client.get(reverse('doctor_dashboard')), 'Penicillin')

    def test_dashboard_query_count_does_not_grow_with_appointments(self):
        for hour in (9, 10, 11):
            self.book(appointment_time=time(hour, 0))
        self.client.force_login(self.doctor)
        # session, user, working-hours check, appointments with patient profiles
        with self.assertNumQueries(4):
            self.client.get(reverse('doctor_dashboard'))
