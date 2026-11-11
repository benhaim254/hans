from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView

from .forms import DoctorProfileForm, PatientProfileForm, SignUpForm
from .models import ROLE_ADMIN, ROLE_DOCTOR, ROLE_PATIENT, DoctorProfile, PatientProfile
from .serializers import CustomTokenObtainPairSerializer, RegisterSerializer

PROFILE_FORMS = {
    ROLE_PATIENT: (PatientProfile, PatientProfileForm),
    ROLE_DOCTOR: (DoctorProfile, DoctorProfileForm),
}


# --- API ---

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class RegisterView(CreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer


# --- HTML ---

def redirect_by_role(user):
    if user.role == ROLE_DOCTOR:
        return redirect('doctor_dashboard')
    if user.role == ROLE_ADMIN:
        return redirect('admin:index')
    return redirect('patient_dashboard')


def index(request):
    if not request.user.is_authenticated:
        return redirect('users:login')
    return redirect_by_role(request.user)


def login_view(request):
    if request.user.is_authenticated:
        return redirect_by_role(request.user)
    if request.method == 'POST':
        user = authenticate(request,
                            username=request.POST.get('username'),
                            password=request.POST.get('password'))
        if user:
            login(request, user)
            next_url = request.POST.get('next', '')
            # Only follow ?next= to this site, never to an outside address.
            if url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()},
                                               require_https=request.is_secure()):
                return redirect(next_url)
            return redirect_by_role(user)
        return render(request, 'users/login.html', {'error': 'Invalid username or password',
                                                    'next': request.POST.get('next', '')})
    return render(request, 'users/login.html', {'next': request.GET.get('next', '')})


@require_POST
def logout_view(request):
    logout(request)
    return redirect('users:login')


def register_view(request):
    if request.user.is_authenticated:
        return redirect_by_role(request.user)
    form = SignUpForm(request.POST or None)
    if form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, 'Welcome to HANS. Complete your profile below.')
        return redirect('users:profile_edit')
    return render(request, 'users/register.html', {'form': form})


@login_required
def profile_edit(request):
    if request.user.role not in PROFILE_FORMS:
        raise Http404('This account has no profile.')
    model, form_class = PROFILE_FORMS[request.user.role]
    profile, _ = model.objects.get_or_create(user=request.user)
    form = form_class(request.POST or None, instance=profile)
    if form.is_valid():
        form.save()
        messages.success(request, 'Profile saved.')
        return redirect_by_role(request.user)
    return render(request, 'users/profile_edit.html', {'form': form})
