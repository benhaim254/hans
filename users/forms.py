from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import SELF_SERVICE_ROLES, DoctorProfile, PatientProfile, User


class SignUpForm(UserCreationForm):
    role = forms.ChoiceField(choices=SELF_SERVICE_ROLES, label='I am a')

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ['username', 'email', 'role']


DATE_INPUT = forms.DateInput(attrs={'type': 'date'})


class PatientProfileForm(forms.ModelForm):
    class Meta:
        model = PatientProfile
        exclude = ['user']
        widgets = {'date_of_birth': DATE_INPUT}


class DoctorProfileForm(forms.ModelForm):
    class Meta:
        model = DoctorProfile
        exclude = ['user']
        widgets = {'date_of_birth': DATE_INPUT}
