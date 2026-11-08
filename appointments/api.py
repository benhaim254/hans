from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import mixins, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from users.models import ROLE_DOCTOR, ROLE_PATIENT
from users.permissions import IsDoctor, IsPatient

from .models import Appointment
from .serializers import AppointmentSerializer, CancelSerializer


class AppointmentViewSet(mixins.ListModelMixin,
                         mixins.RetrieveModelMixin,
                         mixins.CreateModelMixin,
                         viewsets.GenericViewSet):
    """
    Patients book and cancel their own appointments.
    Doctors see and confirm appointments assigned to them.
    """
    serializer_class = AppointmentSerializer
    lookup_field = 'appointment_id'

    def get_permissions(self):
        if self.action in ('create', 'cancel'):
            return [IsPatient()]
        if self.action == 'confirm':
            return [IsDoctor()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        queryset = Appointment.objects.select_related('patient', 'doctor')
        if user.role == ROLE_PATIENT:
            return queryset.filter(patient=user)
        if user.role == ROLE_DOCTOR:
            return queryset.filter(doctor=user)
        return queryset.none()

    def perform_create(self, serializer):
        serializer.save(patient=self.request.user)

    def _transition(self, change):
        appointment = self.get_object()
        try:
            change(appointment)
        except DjangoValidationError as error:
            raise serializers.ValidationError({'detail': error.messages[0]})
        return Response(self.get_serializer(appointment).data)

    @action(detail=True, methods=['post'])
    def confirm(self, request, appointment_id=None):
        return self._transition(lambda appointment: appointment.confirm())

    @action(detail=True, methods=['post'])
    def cancel(self, request, appointment_id=None):
        body = CancelSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        reason = body.validated_data['cancellation_reason']
        return self._transition(lambda appointment: appointment.cancel(reason))
