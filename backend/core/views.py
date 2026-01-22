from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.views import api_view


@api_view(["GET"])
def health_check(request):
    return Response({"status": "ok"})
