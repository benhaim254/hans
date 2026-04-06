from django.shortcuts import render
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import CustomTokenObtainPairSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.contrib.auth import get_user_model

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
        
        user = User.objects.create_user(username=username, password=password,)
        user.role = role
        user.save()
        return Response(
            {'message': f'User {username} create with role {role}'},
            status=status.HTTP_201_CREATED
            )
def index(request):
    """
    View to display all users in the system.
    This is a simple view that retrieves all users and renders them in a template.
    """
    
    users = User.objects.filter(
        role__in=[User.ROLE_PATIENT, User.ROLE_DOCTOR
                  ])
    context = {'users': users}
    return render(request, 'users/index.html', context)