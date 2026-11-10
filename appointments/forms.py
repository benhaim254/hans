from django import forms

from hans.forms import BootstrapFormMixin
from users.models import ROLE_DOCTOR, User

from .models import Appointment


class AppointmentForm(BootstrapFormMixin, forms.ModelForm):
    doctor = forms.ModelChoiceField(
        queryset=User.objects.filter(role=ROLE_DOCTOR),
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
            'appointment_time': forms.TimeInput(attrs={'type': 'time'}),
        }


class CancelAppointmentForm(forms.Form):
    cancellation_reason = forms.CharField(
        label='Reason for canceling',
        max_length=500,
        widget=forms.TextInput(attrs={'placeholder': 'Reason for canceling'}),
    )
