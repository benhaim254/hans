from datetime import time, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from appointments.models import Appointment, WorkingHours
from users.models import ROLE_DOCTOR, ROLE_PATIENT, DoctorProfile, KmpdcRegister, User

DEMO_PASSWORD = 'hans-demo-2026'

# The local KMPDC register holds exactly these three numbers, one per demo doctor.
# Each doctor works Monday to Friday, 08:00 to 17:00, with their own appointment length.
DOCTORS = [
    ('dr_amina', 'Amina', 'Wanjiru', 'cardiology', 'Interventional cardiology', 'A10234', 30),
    ('dr_otieno', 'Brian', 'Otieno', 'pediatrics', 'Neonatal care', 'A10567', 45),
    ('dr_njeri', 'Grace', 'Njeri', 'dermatology', 'Skin conditions', 'A10891', 60),
]
WORKDAYS = range(5)  # Monday to Friday


def next_workday(start, skip):
    """The workday `skip` workdays after `start` (1 = the next workday)."""
    day = start
    while skip:
        day += timedelta(days=1)
        if day.weekday() in WORKDAYS:
            skip -= 1
    return day
PATIENTS = [
    ('jane', 'Jane', 'Achieng'),
    ('peter', 'Peter', 'Kamau'),
]


class Command(BaseCommand):
    help = f"Create demo doctors, patients and appointments. Every demo account uses the password '{DEMO_PASSWORD}'."

    def add_arguments(self, parser):
        parser.add_argument('--with-admin', action='store_true',
                            help="Also create an 'admin' superuser with the demo password.")

    @transaction.atomic
    def handle(self, *args, **options):
        doctors = [self._user(username, first, last, ROLE_DOCTOR) for username, first, last, *_ in DOCTORS]
        for doctor, (_, first, last, department, specialization, number, length) in zip(doctors, DOCTORS):
            entry, _ = KmpdcRegister.objects.get_or_create(
                license_number=number, defaults={'full_name': f'Dr. {first} {last}'})
            if DoctorProfile.objects.filter(kmpdc=entry).exclude(user=doctor).exists():
                self.stderr.write(f"KMPDC {number} already belongs to another account; {doctor.username} stays unverified.")
                entry = None
            DoctorProfile.objects.filter(user=doctor).update(
                department=department, specialization=specialization, appointment_length=length,
                kmpdc=entry)
            for weekday in WORKDAYS:
                WorkingHours.objects.get_or_create(
                    doctor=doctor, weekday=weekday,
                    defaults={'start_time': time(8, 0), 'end_time': time(17, 0)})
        patients = [self._user(username, first, last, ROLE_PATIENT) for username, first, last in PATIENTS]

        today = timezone.localdate()
        slots = [
            (patients[0], doctors[0], next_workday(today, 1), time(9, 0), 'Chest pain follow-up'),
            (patients[0], doctors[1], next_workday(today, 3), time(14, 30), 'Child vaccination'),
            (patients[1], doctors[0], next_workday(today, 2), time(11, 0), 'Blood pressure review'),
        ]
        for patient, doctor, day, at, reason in slots:
            Appointment.objects.get_or_create(
                doctor=doctor, appointment_date=day, appointment_time=at,
                defaults={'patient': patient, 'reason': reason})

        if options['with_admin'] and not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@hans.local', DEMO_PASSWORD)

        names = ', '.join(u.username for u in doctors + patients)
        self.stdout.write(self.style.SUCCESS(f"Demo data ready. Log in as {names} with password '{DEMO_PASSWORD}'."))

    def _user(self, username, first, last, role):
        user, created = User.objects.get_or_create(
            username=username,
            defaults={'first_name': first, 'last_name': last, 'role': role,
                      'email': f'{username}@hans.local'})
        if created:
            user.set_password(DEMO_PASSWORD)
            user.save(update_fields=['password'])
        return user
