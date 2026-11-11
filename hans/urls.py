from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from appointments.api import AppointmentViewSet, doctor_slots
from users.views import CustomTokenObtainPairView, RegisterView

router = DefaultRouter()
router.register('appointments', AppointmentViewSet, basename='appointment')

urlpatterns = [
    path('admin/', admin.site.urls),
    # REST API (JWT)
    path('api/', include(router.urls)),
    path('api/doctors/<int:doctor_id>/slots/', doctor_slots, name='doctor_slots'),
    path('api/register/', RegisterView.as_view(), name='api_register'),
    path('api/token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    # Browser app (sessions)
    path('', include('users.urls')),
    path('appointments/', include('appointments.urls')),
    path('notifications/', include('notifications.urls')),
]
