# HANS

[![CI](https://github.com/benhaim254/hans/actions/workflows/ci.yml/badge.svg)](https://github.com/benhaim254/hans/actions/workflows/ci.yml)

HANS (Health Appointment and Notification System) is a Django app for booking clinic appointments. Patients request a slot with a doctor, the doctor confirms it, and both sides get a notification when anything changes. The same rules are available two ways: a server-rendered web app with session login, and a REST API with JWT auth.

I built it as a learning project and portfolio piece, one module at a time.

## What it does

Patients can:
- register, log in and fill in a profile (blood group, allergies, emergency contact)
- book an appointment with a doctor for a future date and time
- cancel a pending or confirmed appointment, giving a reason
- see notifications about their bookings

Doctors can:
- register, log in and fill in a profile (department, specialization, license number)
- see the appointments booked with them and confirm pending ones
- get notified when a patient books or cancels

Admins manage users, profiles, appointments and notifications in the Django admin. Running `createsuperuser` gives the account the admin role.

## Design notes

- Roles live on a custom `User` model (`patient`, `doctor`, `admin`). Web views use a `role_required` decorator and API views use DRF permission classes (`IsPatient`, `IsDoctor`). Each user only ever sees their own appointments; asking for someone else's returns 404.
- Self-registration can create patients and doctors, never admins. Doctor accounts are not verified against a license register, which a real deployment would need.
- A doctor cannot be double-booked. A partial unique constraint on `(doctor, date, time)` enforces it in the database and ignores canceled appointments, so canceling frees the slot. `Appointment.clean()` runs the same check first so the form and the API return a readable error.
- Status changes go through `Appointment.confirm()` and `Appointment.cancel()`, so the web views and the API share one set of transition rules.
- The `notifications` app listens to appointment saves. It stores a `Notification` row and emails the user once the transaction commits. In development, emails print to the terminal.
- Profiles (`PatientProfile`, `DoctorProfile`) are created automatically by a `post_save` signal when a user signs up.

## Tech stack

- Python 3.12, Django 6.0, Django REST Framework, Simple JWT
- Bootstrap 5 for the web pages, Django Unfold for the admin site
- SQLite for development
- uv for dependencies, python-decouple for settings
- GitHub Actions running system checks, a migrations check and the test suite

## Getting started

You need Python 3.12 and [uv](https://docs.astral.sh/uv/).

```
git clone https://github.com/benhaim254/hans.git
cd hans
uv sync
cp .env.example .env    # then set SECRET_KEY to a long random string
uv run python manage.py migrate
uv run python manage.py seed_demo --with-admin
uv run python manage.py runserver
```

Open http://127.0.0.1:8000/. The seed command creates these accounts, all with the password `hans-demo-2026`:

| Username | Role |
|---|---|
| `jane`, `peter` | patient |
| `dr_amina`, `dr_otieno` | doctor |
| `admin` | admin (only with `--with-admin`) |

The Django admin is at http://127.0.0.1:8000/admin/.

To generate a secret key:

```
uv run python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

## REST API

| Method | Path | Who | What |
|---|---|---|---|
| POST | `/api/register/` | anyone | create a patient or doctor account |
| POST | `/api/token/` | anyone | get access and refresh tokens (the access token carries the user's role) |
| POST | `/api/token/refresh/` | anyone | refresh an access token |
| GET | `/api/appointments/` | patient, doctor | list your own appointments |
| POST | `/api/appointments/` | patient | book an appointment |
| GET | `/api/appointments/<uuid>/` | patient, doctor | one of your appointments |
| POST | `/api/appointments/<uuid>/confirm/` | doctor | confirm a pending appointment |
| POST | `/api/appointments/<uuid>/cancel/` | patient | cancel, with `cancellation_reason` |

Example:

```
TOKEN=$(curl -s -X POST localhost:8000/api/token/ -d username=jane -d password=hans-demo-2026 \
  | python -c "import sys, json; print(json.load(sys.stdin)['access'])")
curl -H "Authorization: Bearer $TOKEN" localhost:8000/api/appointments/
```

## Running the tests

```
uv run python manage.py test
```

## Branches

- `main` holds finished, working releases. It only changes by merging `dev`.
- `dev` is where work comes together. Feature branches start from `dev` and merge back into it through a pull request.

CI runs on every push to `main` and `dev` and on every pull request into them.

## Project layout

```
hans/            settings and root URLs (web routes plus the /api/ router)
users/           custom User, profiles, registration, login, role checks
appointments/    Appointment model, web views, API viewset, seed_demo command
notifications/   Notification model and the signals that create them
templates/       server-rendered pages
```

## What's next

- Structured doctor availability, so patients can only pick open slots
- Reminder notifications the day before an appointment, and SMS
- Production settings: Postgres, static files with WhiteNoise, a Dockerfile

## Author

Benjamin Owuor Ouma
- GitHub: [@benhaim254](https://github.com/benhaim254)
- LinkedIn: [benjamin-owuor-bb4838261](https://linkedin.com/in/benjamin-owuor-bb4838261)
