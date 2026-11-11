from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import ROLE_DOCTOR, SELF_SERVICE_ROLES, User, claim_kmpdc


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['role'] = user.role
        return token


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    role = serializers.ChoiceField(choices=SELF_SERVICE_ROLES)
    kmpdc_number = serializers.CharField(write_only=True, required=False, allow_blank=True, max_length=20)

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password', 'role', 'kmpdc_number']

    def validate(self, attrs):
        number = attrs.pop('kmpdc_number', '')
        attrs['kmpdc_entry'] = None
        if attrs['role'] == ROLE_DOCTOR:
            if not number:
                raise serializers.ValidationError({'kmpdc_number': 'Doctors must give their KMPDC number.'})
            try:
                attrs['kmpdc_entry'] = claim_kmpdc(number)
            except DjangoValidationError as error:
                raise serializers.ValidationError({'kmpdc_number': error.messages})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        kmpdc_entry = validated_data.pop('kmpdc_entry')
        user = User.objects.create_user(**validated_data)
        if kmpdc_entry:
            user.doctorprofile.kmpdc = kmpdc_entry
            user.doctorprofile.save(update_fields=['kmpdc'])
        return user
