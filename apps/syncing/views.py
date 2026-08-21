from django.db import transaction
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import CloudSyncEvent, SyncInstallation
from .serializers import SyncEventUploadSerializer
from .services import SyncProjectionError, project_inventory_event


class SyncEventUploadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = SyncEventUploadSerializer(
            data=request.data,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        installation_id = request.headers.get('X-Xantara-Installation-Id', '')
        terminal_id = request.headers.get('X-Xantara-Terminal-Id', '')
        if not installation_id or not terminal_id:
            return Response(
                {'detail': 'Installation and terminal headers are required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        installation = (
            SyncInstallation.objects.select_related('branch')
            .filter(
                business_id=data['businessId'],
                installation_id=installation_id,
                terminal_id=terminal_id,
                local_branch_id=data['branchId'],
                authorized_staff=request.user,
                is_active=True,
                sync_enabled=True,
                branch__active=True,
            )
            .first()
        )
        if installation is None:
            return Response(
                {'detail': 'This installation is not authorized for sync.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        event_values = {
            'installation': installation,
            'branch': installation.branch,
            'local_branch_id': data['branchId'],
            'local_event_id': data['localEventId'],
            'aggregate_type': data['aggregateType'],
            'aggregate_id': data['aggregateId'],
            'event_type': data['eventType'],
            'schema_version': data['schemaVersion'],
            'payload': data['payload'],
            'device_created_at': data['createdAt'],
        }

        try:
            with transaction.atomic():
                event, created = CloudSyncEvent.objects.get_or_create(
                    business_id=data['businessId'],
                    idempotency_key=data['idempotencyKey'],
                    defaults=event_values,
                )
                if not created and not self._matches(event, event_values):
                    return Response(
                        {'detail': 'Idempotency key was reused for another event.'},
                        status=status.HTTP_409_CONFLICT,
                    )
                projected = project_inventory_event(event) if created else False
        except SyncProjectionError as error:
            return Response(
                {'detail': str(error)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                'serverEventId': str(event.pk),
                'acceptedAt': event.accepted_at.isoformat(),
                'inventoryProjected': projected,
            },
            status=(status.HTTP_202_ACCEPTED if created else status.HTTP_200_OK),
        )

    @staticmethod
    def _matches(event, values):
        return all(
            (
                event.installation_id == values['installation'].pk,
                event.branch_id == values['branch'].pk,
                event.local_branch_id == values['local_branch_id'],
                event.local_event_id == values['local_event_id'],
                event.aggregate_type == values['aggregate_type'],
                event.aggregate_id == values['aggregate_id'],
                event.event_type == values['event_type'],
                event.schema_version == values['schema_version'],
                event.payload == values['payload'],
                event.device_created_at == values['device_created_at'],
            )
        )
