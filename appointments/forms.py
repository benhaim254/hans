from datetime import time

from django import forms
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from hans.forms import BootstrapFormMixin
from users.models import APPOINTMENT_LENGTH_CHOICES, User

from .models import WEEKDAYS, Appointment, TimeOff, WorkingHours


class AppointmentForm(BootstrapFormMixin, forms.ModelForm):
    doctor = forms.ModelChoiceField(
        queryset=User.objects.verified_doctors(),
        empty_label="Select a Doctor"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['doctor'].label_from_instance = (
            lambda doctor: f"Dr. {doctor.get_full_name() or doctor.username}")

    class Meta:
        model = Appointment
        fields = ['doctor', 'appointment_date', 'appointment_time', 'reason']
        widgets = {
            'appointment_date': forms.DateInput(attrs={'type': 'date'}),
            # Options are filled in the browser from the free-slots API once a doctor and date are picked.
            'appointment_time': forms.Select(choices=[('', 'Pick a doctor and date first')]),
        }


class CancelAppointmentForm(forms.Form):
    cancellation_reason = forms.CharField(
        label='Reason for canceling',
        max_length=500,
        widget=forms.TextInput(attrs={'placeholder': 'Reason for canceling'}),
    )


class AvailabilityForm(forms.Form):
    """A doctor's appointment length plus one optional working range per weekday."""
    appointment_length = forms.TypedChoiceField(choices=APPOINTMENT_LENGTH_CHOICES, coerce=int,
                                                widget=forms.Select(attrs={'class': 'form-select'}))

    def __init__(self, *args, doctor, **kwargs):
        super().__init__(*args, **kwargs)
        self.doctor = doctor
        self.fields['appointment_length'].initial = doctor.doctorprofile.appointment_length
        existing = {hours.weekday: hours for hours in doctor.working_hours.all()}
        time_input = {'type': 'time', 'class': 'form-control form-control-sm'}
        for day, name in WEEKDAYS:
            hours = existing.get(day)
            self.fields[f'works_{day}'] = forms.BooleanField(
                required=False, initial=hours is not None, label=name,
                widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
            self.fields[f'start_{day}'] = forms.TimeField(
                required=False, initial=hours.start_time if hours else time(8, 0),
                label=f'{name} start', widget=forms.TimeInput(attrs=time_input, format='%H:%M'))
            self.fields[f'end_{day}'] = forms.TimeField(
                required=False, initial=hours.end_time if hours else time(17, 0),
                label=f'{name} end', widget=forms.TimeInput(attrs=time_input, format='%H:%M'))

    def days(self):
        """(works, start, end) bound fields per weekday, for the template table."""
        return [(self[f'works_{day}'], self[f'start_{day}'], self[f'end_{day}']) for day, _ in WEEKDAYS]

    def clean(self):
        cleaned = super().clean()
        for day, name in WEEKDAYS:
            if not cleaned.get(f'works_{day}'):
                continue
            start, end = cleaned.get(f'start_{day}'), cleaned.get(f'end_{day}')
            if not start or not end:
                self.add_error(f'start_{day}', f'Give a start and end time for {name}.')
            elif end <= start:
                self.add_error(f'end_{day}', f'{name} must end after it starts.')
        return cleaned

    @transaction.atomic
    def save(self):
        profile = self.doctor.doctorprofile
        profile.appointment_length = self.cleaned_data['appointment_length']
        profile.save(update_fields=['appointment_length'])
        for day, _ in WEEKDAYS:
            if self.cleaned_data[f'works_{day}']:
                WorkingHours.objects.update_or_create(
                    doctor=self.doctor, weekday=day,
                    defaults={'start_time': self.cleaned_data[f'start_{day}'],
                              'end_time': self.cleaned_data[f'end_{day}']})
            else:
                WorkingHours.objects.filter(doctor=self.doctor, weekday=day).delete()


class TimeOffForm(forms.ModelForm):
    class Meta:
        model = TimeOff
        fields = ['start_date', 'end_date', 'reason']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'reason': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Annual leave'}),
        }

    def clean(self):
        cleaned = super().clean()
        start, end = cleaned.get('start_date'), cleaned.get('end_date')
        if start and start < timezone.localdate():
            self.add_error('start_date', 'Time off cannot start in the past.')
        if start and end and end < start:
            self.add_error('end_date', 'The last day cannot be before the first day.')
        return cleaned


class NewTimeForm(BootstrapFormMixin, forms.Form):
    """A new date and free start time, used to propose or reschedule an appointment."""
    appointment_date = forms.DateField(label='New date', widget=forms.DateInput(attrs={'type': 'date'}))
    appointment_time = forms.TimeField(label='New time', widget=forms.Select(choices=[('', 'Pick a date first')]))

    def apply(self, change):
        """Run a model move (propose/reschedule); its rule errors become form errors. True on success."""
        try:
            change(self.cleaned_data['appointment_date'], self.cleaned_data['appointment_time'])
        except ValidationError as error:
            if hasattr(error, 'error_dict'):
                for field, errors in error.error_dict.items():
                    self.add_error(field if field in self.fields else None, errors)
            else:
                self.add_error(None, error)
            return False
        return True
