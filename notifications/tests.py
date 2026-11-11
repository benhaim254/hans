from datetime import time, timedelta
from unittest import mock

from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from appointments.models import Appointment
from users.models import ROLE_DOCTOR, User

from .models import Notification


class AppointmentNotificationTests(TestCase):
    def setUp(self):
        self.patient = User.objects.create_user('pat', email='pat@example.com', password='x')
        self.doctor = User.objects.create_user('doc', email='doc@example.com', password='x', role=ROLE_DOCTOR)

    def book(self):
        with self.captureOnCommitCallbacks(execute=True):
            return Appointment.objects.create(
                patient=self.patient, doctor=self.doctor,
                appointment_date=timezone.localdate() + timedelta(days=1), appointment_time=time(9, 0))

    def test_booking_notifies_both_and_emails(self):
        self.book()
        self.assertEqual(Notification.objects.filter(user=self.patient).count(), 1)
        self.assertEqual(Notification.objects.filter(user=self.doctor).count(), 1)
        self.assertEqual(sorted(m.to[0] for m in mail.outbox), ['doc@example.com', 'pat@example.com'])

    def test_confirm_notifies_patient_once(self):
        appointment = self.book()
        appointment.confirm()
        appointment.reason = 'edited'
        appointment.save()  # status unchanged: no new notification
        self.assertEqual(Notification.objects.filter(user=self.patient).count(), 2)
        self.assertIn('confirmed', Notification.objects.filter(user=self.patient).first().message)

    def test_cancel_notifies_doctor(self):
        appointment = self.book()
        appointment.cancel('Travelling')
        self.assertIn('canceled', Notification.objects.filter(user=self.doctor).first().message)

    def test_list_page_marks_read(self):
        self.book()
        self.client.force_login(self.patient)
        response = self.client.get(reverse('notifications:list'))
        self.assertContains(response, 'awaiting confirmation')
        self.assertFalse(Notification.objects.filter(user=self.patient, is_read=False).exists())


    def test_failed_email_does_not_break_booking(self):
        with mock.patch('notifications.signals.send_mail', side_effect=OSError('mail server down')), \
                self.assertLogs('notifications.signals', level='ERROR'):
            self.book()
        self.assertEqual(Notification.objects.count(), 2)

    def test_unread_count_in_navbar(self):
        self.book()
        self.client.force_login(self.patient)
        response = self.client.get(reverse('users:profile_edit'))
        self.assertEqual(response.context['unread_notifications'], 1)
        self.client.get(reverse('notifications:list'))
        self.assertEqual(self.client.get(reverse('users:profile_edit')).context['unread_notifications'], 0)
