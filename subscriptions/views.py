from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Platform
from .serializers import PlatformSerializer

@api_view(['GET'])
def platform_list(request):
    platforms = Platform.objects.all()
    serializer = PlatformSerializer(platforms, many=True)

    return Response(serializer.data)