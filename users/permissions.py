from rest_framework.permissions import BasePermission

class IsPatient(BasePermission):
    """Allow access only to users with the patient role."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated 
                    and request.user.role == 'patient')
    
class IsDoctor(BasePermission):
    """Allow access only to users with the doctor role."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated
                    and request.user.role == 'doctor')
    
class IsAdminUser(BasePermission):
    """Allow access only to users with the admin role."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated
                    and request.user.role == 'admin')