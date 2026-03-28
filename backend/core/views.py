from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render


def index(request):
    return HttpResponse("Welcome to the Hans API!")


@login_required
def secret(request):
    return render(request, "core/secret.html")
