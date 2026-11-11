from unittest import mock

from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from .models import ROLE_ADMIN, ROLE_DOCTOR, ROLE_PATIENT, DoctorProfile, KmpdcRegister, PatientProfile, User

STRONG_PASSWORD = 'Str0ng-pass-123'


def make_verified_doctor(username, number=None, **fields):
    """A doctor holding a KMPDC register entry, so patients can book them."""
    doctor = User.objects.create_user(username, password=fields.pop('password', STRONG_PASSWORD), role=ROLE_DOCTOR, **fields)
    entry = KmpdcRegister.objects.create(license_number=number or f'T-{username}', full_name=username)
    doctor.doctorprofile.kmpdc = entry
    doctor.doctorprofile.save()
    return doctor


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

    def test_doctor_with_register_number_is_verified(self):
        KmpdcRegister.objects.create(license_number='A10234', full_name='Dr. Who')
        response = self.client.post(self.url, {'username': 'dr_who', 'password': STRONG_PASSWORD,
                                               'role': 'doctor', 'kmpdc_number': ' a10234 '})
        self.assertEqual(response.status_code, 201, response.data)
        doctor = User.objects.get(username='dr_who')
        self.assertEqual(doctor.role, ROLE_DOCTOR)
        self.assertEqual(doctor.doctorprofile.kmpdc.license_number, 'A10234')
        self.assertNotIn('password', response.data)
        self.assertNotIn('kmpdc_number', response.data)

    def test_doctor_without_number_rejected(self):
        response = self.client.post(self.url, {'username': 'dr_who', 'password': STRONG_PASSWORD, 'role': 'doctor'})
        self.assertEqual(response.status_code, 400)
        self.assertIn('kmpdc_number', response.data)
        self.assertFalse(User.objects.filter(username='dr_who').exists())

    def test_number_not_on_register_rejected(self):
        response = self.client.post(self.url, {'username': 'dr_who', 'password': STRONG_PASSWORD,
                                               'role': 'doctor', 'kmpdc_number': 'A99999'})
        self.assertEqual(response.status_code, 400)
        self.assertIn('not on the register', str(response.data['kmpdc_number']))

    def test_number_already_claimed_rejected(self):
        make_verified_doctor('dr_first', number='A10234')
        response = self.client.post(self.url, {'username': 'dr_copycat', 'password': STRONG_PASSWORD,
                                               'role': 'doctor', 'kmpdc_number': 'A10234'})
        self.assertEqual(response.status_code, 400)
        self.assertIn('already registered', str(response.data['kmpdc_number']))
        self.assertFalse(User.objects.filter(username='dr_copycat').exists())

    def test_patient_needs_no_number(self):
        response = self.client.post(self.url, {'username': 'pat', 'password': STRONG_PASSWORD, 'role': 'patient'})
        self.assertEqual(response.status_code, 201)

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
    def test_register_page_creates_verified_doctor_and_logs_in(self):
        KmpdcRegister.objects.create(license_number='A10567', full_name='Dr. New')
        response = self.client.post(reverse('users:register'), {
            'username': 'newdoc', 'email': 'd@example.com', 'role': 'doctor', 'kmpdc_number': 'A10567',
            'password1': STRONG_PASSWORD, 'password2': STRONG_PASSWORD,
        })
        self.assertRedirects(response, reverse('users:profile_edit'))
        doctor = User.objects.get(username='newdoc')
        self.assertEqual(doctor.role, ROLE_DOCTOR)
        self.assertEqual(doctor.doctorprofile.kmpdc.license_number, 'A10567')

    def test_register_page_rejects_claimed_number(self):
        make_verified_doctor('dr_first', number='A10567')
        response = self.client.post(reverse('users:register'), {
            'username': 'copycat', 'role': 'doctor', 'kmpdc_number': 'A10567',
            'password1': STRONG_PASSWORD, 'password2': STRONG_PASSWORD,
        })
        self.assertContains(response, 'already registered to another account')
        self.assertFalse(User.objects.filter(username='copycat').exists())

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

    def test_login_returns_to_requested_page(self):
        User.objects.create_user('pat', password=STRONG_PASSWORD)
        page = reverse('notifications:list')
        self.assertContains(self.client.get(reverse('users:login'), {'next': page}), f'value="{page}"')
        response = self.client.post(reverse('users:login'), {'username': 'pat', 'password': STRONG_PASSWORD, 'next': page})
        self.assertRedirects(response, page)

    def test_login_ignores_outside_next(self):
        User.objects.create_user('pat', password=STRONG_PASSWORD)
        response = self.client.post(reverse('users:login'), {
            'username': 'pat', 'password': STRONG_PASSWORD, 'next': 'https://evil.example.com/'})
        self.assertRedirects(response, reverse('patient_dashboard'))

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



class RoleAndRegisterReviewTests(TestCase):
    def test_register_admin_form_catches_spaced_duplicate(self):
        KmpdcRegister.objects.create(license_number='A1', full_name='Dr. One')
        root = User.objects.create_superuser('root', 'root@example.com', STRONG_PASSWORD)
        self.client.force_login(root)
        response = self.client.post(reverse('admin:users_kmpdcregister_add'), {'license_number': ' a1 ', 'full_name': 'Dr. Two'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(KmpdcRegister.objects.count(), 1)

    def test_role_change_gives_new_profile_and_releases_kmpdc(self):
        doctor = make_verified_doctor('doc', number='A1')
        doctor.role = ROLE_PATIENT
        doctor.save()
        self.assertTrue(PatientProfile.objects.filter(user=doctor).exists())
        self.assertIsNone(DoctorProfile.objects.get(user=doctor).kmpdc)
        self.assertFalse(User.objects.verified_doctors().filter(pk=doctor.pk).exists())

        patient = User.objects.create_user('pat', password=STRONG_PASSWORD)
        patient.role = ROLE_DOCTOR
        patient.save()
        self.assertTrue(DoctorProfile.objects.filter(user=patient).exists())

    def test_login_save_does_not_touch_profiles(self):
        doctor = make_verified_doctor('doc', number='A1')
        with self.assertNumQueries(1):
            doctor.save(update_fields=['last_login'])

    def test_admin_role_gets_staff_access(self):
        user = User.objects.create_user('ops', password=STRONG_PASSWORD, role=ROLE_ADMIN)
        self.assertTrue(user.is_staff)
        self.client.force_login(user)
        self.assertRedirects(self.client.get(reverse('users:index')), reverse('admin:index'), target_status_code=200)

    def test_simultaneous_signup_returns_error_not_500(self):
        with mock.patch('users.serializers.User.objects.create_user', side_effect=IntegrityError):
            response = APIClient().post(reverse('api_register'), {'username': 'pat', 'password': STRONG_PASSWORD, 'role': 'patient'})
        self.assertEqual(response.status_code, 400)
        with mock.patch('users.forms.SignUpForm.save', side_effect=IntegrityError):
            response = self.client.post(reverse('users:register'), {
                'username': 'pat2', 'role': 'patient', 'password1': STRONG_PASSWORD, 'password2': STRONG_PASSWORD})
        self.assertContains(response, 'at the same moment')
