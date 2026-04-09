from .serializers import CustomTokenObtainPairSerializer
from django.shortcuts import render, redirect
from django.contrib.auth import get_user_model, authenticate, login, logout
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from .permissions import IsPatient, IsDoctor

User = get_user_model()

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        role = request.data.get('role')
        
        if not username or not password or not role:
            return Response(
                {'error': 'username, password and role are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if User.objects.filter(username=username).exists():
            return Response(
                {'error': 'username already taken'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user = User.objects.create_user(username=username, password=password)
        return Response(
            {'message': f'User {username} create with role {role}'},
            status=status.HTTP_201_CREATED
            )
class PatientOnlyView(APIView):
    permission_classes = [IsPatient]

    def get(self,request):
        return Response({'message': f'Hello {request.user.username}'})
    
class DoctorOnlyView(APIView):
    permission_classes = [IsDoctor]

    def get(self, request):
        return Response ({'message': f'Hello Dr.{request.user.username}'})

def login_view(request):
    if request.user.is_authenticated:
        return redirect_by_role(request.user)
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect_by_role(user)
        else:
            return render(request, 'users/login.html', {'error': 'Invalid username or password'})
    return render(request, 'users/login.html')

def logout_view(request):
    logout(request)
    return redirect('users:login')

def redirect_by_role(user):
    if user.role == 'doctor':
        return redirect('doctor_dashboard')
    return redirect('patient_dashboard')

def index(request):
    if not request.user.is_authenticated:
        return redirect('users:login')
    return redirect_by_role(request.user)