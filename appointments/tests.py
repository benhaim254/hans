from datetime import time, timedelta
from io import StringIO

from django.core.management import call_command
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from users.models import ROLE_DOCTOR, ROLE_PATIENT, User
from users.tests import make_verified_doctor

from .models import STATUS_CANCELED, STATUS_PENDING, STATUS_SCHEDULED, Appointment

TOMORROW = timezone.localdate() + timedelta(days=1)


class AppointmentTestCase(TestCase):
    def setUp(self):
        self.patient = User.objects.create_user('pat', password='x', role=ROLE_PATIENT)
        self.other_patient = User.objects.create_user('pat2', password='x', role=ROLE_PATIENT)
        self.doctor = make_verified_doctor('doc')
        self.other_doctor = make_verified_doctor('doc2')

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
        self.assertEqual(Appointment.objects.count(), 3)
