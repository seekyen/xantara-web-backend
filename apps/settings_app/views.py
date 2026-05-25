from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import serializers
from .models import StoreSettings

class StoreSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model   = StoreSettings
        exclude = ['id']

class StoreSettingsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(StoreSettingsSerializer(StoreSettings.get_settings()).data)

    def patch(self, request):
        if request.user.role != 'admin':
            return Response({'error': 'Admin only'}, status=403)
        s = StoreSettingsSerializer(
            StoreSettings.get_settings(), data=request.data, partial=True
        )
        if s.is_valid():
            s.save()
            return Response(s.data)
        return Response(s.errors, status=400)
