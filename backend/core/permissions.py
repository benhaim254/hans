from rest_framework import permissions


class IsPatient(permissions.BasePermission):
    """
    Permission class to check if the user is a patient.
    """

    message = "You must be a patient to perform this action."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == "patient"
        )


class IsDoctor(permissions.BasePermission):
    """
    Permission class to check if the user is a doctor.
    """

    message = "You must be a doctor to perform this action."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == "doctor"
        )


class IsAdminUser(permissions.BasePermission):
    """
    Permission class to check if the user is an admin.
    """

    message = "You must be an admin to perform this action."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == "admin"
        )


class IsPatientOrDoctor(permissions.BasePermission):
    """
    Permission class to check if the user is a patient or a doctor.
    """

    message = "You must be a patient or a doctor to perform this action."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role in ["patient", "doctor"]
        )


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Object-level permission to only allow owners or admins to edit/view an object.
    """

    message = "You must be the owner or an admin to perform this action."

    def has_object_permission(self, request, view, obj):
        if request.user.role == "admin":
            return True

        if hasattr(obj, "user"):
            return obj.user == request.user

        if hasattr(obj, "patient"):
            return obj.patient == request.user

        if obj == request.user:
            return True

        return False


class IsAppointmentParticipant(permissions.BasePermission):
    """
    Permission for appointment participants (patient or doctor).
    """

    message = "You must be a participant of this appointment to perform this action."

    def has_object_permission(self, request, view, obj):
        if request.user.role == "admin":
            return True

        return obj.patient == request.user or obj.doctor == request.user


class CanManageAppointmnets(permissions.BasePermission):
    """
    Permission to manage appointments.
    Patients can create and view their own appointments.
    Doctors can view and update appointments assigned to them.
    Admins have full access.
    """

    message = "You do not have permission to manage appointments."

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated

        return (
            request.user
            and request.user.is_authenticated
            and request.user.role in ["patient", "doctor", "admin"]
        )

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return (
                request.user.role == "admin"
                or obj.patient == request.user
                or obj.doctor == request.user
            )

        if request.user.role == "admin":
            return True

        if request.user.role == "patient" and obj.patient == request.user:
            return True

        if request.user.role == "doctor" and obj.doctor == request.user:
            return True

        return False
