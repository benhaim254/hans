from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_date
from rest_framework import mixins, serializers, viewsets
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import action, api_view, authentication_classes, permission_classes
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from users.models import ROLE_DOCTOR, ROLE_PATIENT, User
from users.permissions import IsDoctor, IsPatient

from .models import DOUBLE_BOOKED_MESSAGE, Appointment, available_slots
from .serializers import AppointmentSerializer, CancelSerializer, NewTimeSerializer


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
        if self.action in ('create', 'cancel', 'accept', 'reschedule'):
            return [IsPatient()]
        if self.action in ('confirm', 'complete', 'no_show', 'decline', 'propose'):
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
        try:
            with transaction.atomic():
                serializer.save(patient=self.request.user)
        except IntegrityError:  # someone took the same slot between validation and the insert
            raise serializers.ValidationError({'detail': DOUBLE_BOOKED_MESSAGE})

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
    def complete(self, request, appointment_id=None):
        return self._transition(lambda appointment: appointment.complete())

    @action(detail=True, methods=['post'], url_path='no-show')
    def no_show(self, request, appointment_id=None):
        return self._transition(lambda appointment: appointment.mark_no_show())

    @action(detail=True, methods=['post'])
    def decline(self, request, appointment_id=None):
        body = CancelSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        reason = body.validated_data['cancellation_reason']
        return self._transition(lambda appointment: appointment.decline(reason))

    @action(detail=True, methods=['post'])
    def propose(self, request, appointment_id=None):
        body = NewTimeSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        new = body.validated_data
        return self._transition(lambda appointment: appointment.propose(new['appointment_date'], new['appointment_time']))

    @action(detail=True, methods=['post'])
    def reschedule(self, request, appointment_id=None):
        body = NewTimeSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        new = body.validated_data
        return self._transition(lambda appointment: appointment.reschedule(new['appointment_date'], new['appointment_time']))

    @action(detail=True, methods=['post'])
    def accept(self, request, appointment_id=None):
        return self._transition(lambda appointment: appointment.accept_proposal())

    @action(detail=True, methods=['post'])
    def cancel(self, request, appointment_id=None):
        body = CancelSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        reason = body.validated_data['cancellation_reason']
        return self._transition(lambda appointment: appointment.cancel(reason))


@api_view(['GET'])
# Session auth too, so the booking page can call this with the logged-in browser session.
@authentication_classes([JWTAuthentication, SessionAuthentication])
@permission_classes([IsAuthenticated])
def doctor_slots(request, doctor_id):
    """Free start times for a verified doctor on ?date=YYYY-MM-DD."""
    doctor = get_object_or_404(User.objects.verified_doctors(), pk=doctor_id)
    try:
        day = parse_date(request.query_params.get('date', ''))
    except ValueError:  # well-formed but impossible, e.g. 2026-02-30
        day = None
    if day is None:
        raise serializers.ValidationError({'date': 'Use the format YYYY-MM-DD.'})
    return Response({
        'date': day.isoformat(),
        'duration_minutes': doctor.doctorprofile.appointment_length,
        'slots': [slot.strftime('%H:%M') for slot in available_slots(doctor, day)],
    })
