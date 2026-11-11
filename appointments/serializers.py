from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from users.models import User

from .models import Appointment


class AppointmentSerializer(serializers.ModelSerializer):
    doctor = serializers.PrimaryKeyRelatedField(queryset=User.objects.verified_doctors())
    patient = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Appointment
        fields = [
            'appointment_id', 'patient', 'doctor', 'appointment_date', 'appointment_time',
            'duration_minutes', 'reason', 'status', 'cancellation_reason', 'created_at', 'last_updated',
        ]
        read_only_fields = [
            'appointment_id', 'duration_minutes', 'status', 'cancellation_reason', 'created_at', 'last_updated',
        ]

    def validate(self, attrs):
        # Reuse the model's booking rules so the API and HTML form agree.
        try:
            Appointment(**attrs).clean()
        except DjangoValidationError as error:
            raise serializers.ValidationError(serializers.as_serializer_error(error))
        return attrs


class CancelSerializer(serializers.Serializer):
    cancellation_reason = serializers.CharField(max_length=500)


class NewTimeSerializer(serializers.Serializer):
    appointment_date = serializers.DateField()
    appointment_time = serializers.TimeField()
