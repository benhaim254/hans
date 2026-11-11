from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from django.db import transaction

from hans.forms import BootstrapFormMixin

from .models import ROLE_DOCTOR, SELF_SERVICE_ROLES, DoctorProfile, PatientProfile, User, claim_kmpdc


class SignUpForm(BootstrapFormMixin, UserCreationForm):
    role = forms.ChoiceField(choices=SELF_SERVICE_ROLES, label='I am a')
    kmpdc_number = forms.CharField(label='KMPDC number', max_length=20, required=False,
                                   help_text='Required for doctors. We check it against the KMPDC register.')

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ['first_name', 'last_name', 'username', 'email', 'role']

    def clean(self):
        cleaned = super().clean()
        self.kmpdc_entry = None
        if cleaned.get('role') == ROLE_DOCTOR:
            if not cleaned.get('kmpdc_number'):
                self.add_error('kmpdc_number', 'Doctors must give their KMPDC number.')
            else:
                try:
                    self.kmpdc_entry = claim_kmpdc(cleaned['kmpdc_number'])
                except ValidationError as error:
                    self.add_error('kmpdc_number', error)
        return cleaned

    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit and self.kmpdc_entry:
            user.doctorprofile.kmpdc = self.kmpdc_entry
            user.doctorprofile.save(update_fields=['kmpdc'])
        return user


DATE_INPUT = forms.DateInput(attrs={'type': 'date'})


class PatientProfileForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = PatientProfile
        exclude = ['user']
        widgets = {'date_of_birth': DATE_INPUT}


class DoctorProfileForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = DoctorProfile
        exclude = ['user', 'kmpdc']
        widgets = {'date_of_birth': DATE_INPUT}
