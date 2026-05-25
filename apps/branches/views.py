from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Branch
from .serializers import BranchSerializer
from utils.permissions import IsAdminOrManager

class BranchViewSet(viewsets.ModelViewSet):
    queryset           = Branch.objects.all()
    serializer_class   = BranchSerializer
    permission_classes = [IsAuthenticated]
    search_fields      = ['name','address']
    ordering           = ['name']

    def get_permissions(self):
        if self.action in ('create','update','partial_update','destroy'):
            return [IsAdminOrManager()]
        return [IsAuthenticated()]
