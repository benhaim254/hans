from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from .models import ROLE_ADMIN, ROLE_DOCTOR, ROLE_PATIENT, DoctorProfile, PatientProfile, User

STRONG_PASSWORD = 'Str0ng-pass-123'


class ProfileSignalTests(TestCase):
    def test_patient_gets_patient_profile(self):
        user = User.objects.create_user('pat', password=STRONG_PASSWORD, role=ROLE_PATIENT)
        self.assertTrue(PatientProfile.objects.filter(user=user).exists())
        self.assertFalse(DoctorProfile.objects.filter(user=user).exists())

    def test_doctor_gets_doctor_profile(self):
        user = User.objects.create_user('doc', password=STRONG_PASSWORD, role=ROLE_DOCTOR)
        self.assertTrue(DoctorProfile.objects.filter(user=user).exists())

    def test_superuser_is_admin_without_profile(self):
        user = User.objects.create_superuser('root', 'root@example.com', STRONG_PASSWORD)
        self.assertEqual(user.role, ROLE_ADMIN)
        self.assertFalse(PatientProfile.objects.filter(user=user).exists())


class RegisterApiTests(TestCase):
    url = reverse('api_register')

    def setUp(self):
        self.client = APIClient()

    def test_role_is_saved(self):
        response = self.client.post(self.url, {'username': 'dr_who', 'password': STRONG_PASSWORD, 'role': 'doctor'})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(User.objects.get(username='dr_who').role, ROLE_DOCTOR)
        self.assertNotIn('password', response.data)

    def test_admin_role_is_rejected(self):
        response = self.client.post(self.url, {'username': 'sneaky', 'password': STRONG_PASSWORD, 'role': 'admin'})
        self.assertEqual(response.status_code, 400)
        self.assertFalse(User.objects.filter(username='sneaky').exists())

    def test_duplicate_username_and_weak_password_rejected(self):
        User.objects.create_user('taken', password=STRONG_PASSWORD)
        response = self.client.post(self.url, {'username': 'taken', 'password': '123', 'role': 'patient'})
        self.assertEqual(response.status_code, 400)
        self.assertIn('username', response.data)
        self.assertIn('password', response.data)

    def test_token_carries_role(self):
        User.objects.create_user('doc', password=STRONG_PASSWORD, role=ROLE_DOCTOR)
        response = self.client.post(reverse('token_obtain_pair'), {'username': 'doc', 'password': STRONG_PASSWORD})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(AccessToken(response.data['access'])['role'], ROLE_DOCTOR)


class WebAuthTests(TestCase):
    def test_register_page_creates_doctor_and_logs_in(self):
        response = self.client.post(reverse('users:register'), {
            'username': 'newdoc', 'email': 'd@example.com', 'role': 'doctor',
            'password1': STRONG_PASSWORD, 'password2': STRONG_PASSWORD,
        })
        self.assertRedirects(response, reverse('users:profile_edit'))
        self.assertEqual(User.objects.get(username='newdoc').role, ROLE_DOCTOR)

    def test_register_page_rejects_admin_role(self):
        response = self.client.post(reverse('users:register'), {
            'username': 'x', 'role': 'admin', 'password1': STRONG_PASSWORD, 'password2': STRONG_PASSWORD,
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='x').exists())

    def test_login_redirects_by_role(self):
        User.objects.create_user('doc', password=STRONG_PASSWORD, role=ROLE_DOCTOR)
        response = self.client.post(reverse('users:login'), {'username': 'doc', 'password': STRONG_PASSWORD})
        self.assertRedirects(response, reverse('doctor_dashboard'))

    def test_logout_requires_post(self):
        user = User.objects.create_user('pat', password=STRONG_PASSWORD)
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse('users:logout')).status_code, 405)
        self.client.post(reverse('users:logout'))
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_profile_edit_updates_own_profile(self):
        user = User.objects.create_user('pat', password=STRONG_PASSWORD)
        self.client.force_login(user)
        response = self.client.post(reverse('users:profile_edit'), {
            'gender': 'female', 'blood_group': 'O+', 'allergies': 'Penicillin',
        })
        self.assertRedirects(response, reverse('patient_dashboard'))
        user.patientprofile.refresh_from_db()
        self.assertEqual(user.patientprofile.blood_group, 'O+')


class AdminTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser('root', 'root@example.com', STRONG_PASSWORD)
        self.client.force_login(self.admin)

    def test_admin_pages_render(self):
        for name in ['admin:index', 'admin:users_user_changelist', 'admin:users_user_add',
                     'admin:appointments_appointment_changelist', 'admin:notifications_notification_changelist']:
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)

    def test_admin_add_user_hashes_password_and_sets_role(self):
        response = self.client.post(reverse('admin:users_user_add'), {
            'username': 'newdoc', 'usable_password': 'true',
            'password1': STRONG_PASSWORD, 'password2': STRONG_PASSWORD, 'role': ROLE_DOCTOR,
        })
        self.assertEqual(response.status_code, 302, getattr(response, 'context', None) and response.context['adminform'].form.errors)
        user = User.objects.get(username='newdoc')
        self.assertTrue(user.check_password(STRONG_PASSWORD))
        self.assertEqual(user.role, ROLE_DOCTOR)
