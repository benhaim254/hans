# HANS

HANS (Hospital Appointment and Notification System) is a web application that allows patients to schedule appointments with doctors and receive notifications when their appointment time draws near.

## Table of Contents

1. [Introduction](#introduction)
2. [Features](#features)
3. [Tech Stack](#tech-stack)
4. [Project Structure](#project-structure)
5. [Setup](#setup)
   * [Prerequisites](#prerequisites)
   * [Installation](#installation)
   * [Environment Variables](#environment-variables)
   * [Running the App](#running-the-app)
6. [Status](#status)
7. [Author](#author)

## Introduction

HANS is a Django-based hospital management web application built to streamline the appointment process between patients and doctors. It supports three user roles — patients, doctors, and admins — each with a dedicated set of capabilities.

This project is being developed as both a learning exercise and a portfolio piece, with a structured, module-by-module approach.

## Features

### Patient
- Request appointments with doctors
- View current and previous appointment sessions

### Doctor
- Accept, refer, or reschedule appointments
- View their appointment schedule
- Write short notes after sessions

### Admin
- Manage system users and staff
- Handle overall system maintenance

## Tech Stack

* Python 3.12.3
* Django 6.0.3
* SQLite (development) — PostgreSQL (planned for production)
* Django Templates (migrating to HTMX)
* pipenv
* python-decouple

## Project Structure

```
hans/
├── users/                  # User management and profiles
│   └── templates/
├── appointments/           # Appointment scheduling and management
│   └── templates/
├── notifications/          # Appointment notifications
├── .env                    # Environment variables (not committed)
├── Pipfile
└── Pipfile.lock
```

## Setup

### Prerequisites

* Python 3.12.3
* pipenv

### Installation

```
git clone https://github.com/benhaim254/hans.git
cd hans
pipenv install
pipenv shell
```

### Environment Variables

Create a `.env` file in the root directory and set the following:

```
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
```

### Running the App

```
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Once running, navigate to `http://127.0.0.1:8000/` in your browser.  
The admin portal is available at `http://127.0.0.1:8000/admin/`.

## Status

HANS is currently under active development.

**Working:**
- User creation (patients, doctors, admins) via Django admin
- Patient and doctor profile setup via Django admin

**In Progress:**
- Appointment scheduling and management
- Notification system
- Frontend — home page, patient portal, patient signup, doctor portal

## Author

**Benjamin Owuor Ouma**
- GitHub: [@benhaim254](https://github.com/benhaim254)
- LinkedIn: [benjamin-owuor-bb4838261](https://linkedin.com/in/benjamin-owuor-bb4838261)
