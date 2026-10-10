import secrets
from django.core.exceptions import ValidationError as DjangoValidationError
from django.contrib.auth.hashers import make_password, check_password
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.inventory.models import Branch
from apps.syncing.models import SyncInstallation
from .models import StoreSettings
from .fiscal_models import FiscalCompany, FiscalBranch, FiscalTerminal, FiscalAudit


class FiscalAdmin(BasePermission):
    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.is_active and u.status == 'active' and u.role == 'admin')


class CompanySerializer(serializers.ModelSerializer):
    tin = serializers.RegexField(r'^(?!0{9}$)[0-9]{9}$')
    class Meta:
        model = FiscalCompany
        fields = ['registered_name', 'tin', 'address', 'tax_type', 'locked_at']
        read_only_fields = ['locked_at']

    def validate_registered_name(self, value):
        if any(word in value.lower() for word in ['training', 'placeholder', 'configure']):
            raise ValidationError('Enter the actual registered company name.')
        return value


class BranchSerializer(serializers.ModelSerializer):
    branch_code = serializers.RegexField(r'^[0-9]{5}$')
    rdo = serializers.RegexField(r'^[0-9]{3}$')
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    stock_code = serializers.CharField(source='branch.code', read_only=True)
    class Meta:
        model = FiscalBranch
        fields = ['id', 'branch', 'branch_name', 'stock_code', 'branch_code', 'rdo', 'registered_address', 'locked_at']
        read_only_fields = ['locked_at']

    def validate_branch(self, branch):
        if not branch.active:
            raise ValidationError('Choose an active branch.')
        return branch

    def validate_branch_code(self, code):
        qs = FiscalBranch.objects.filter(branch_code=code)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError('This fiscal branch code is already assigned.')
        return code


class TerminalSerializer(serializers.ModelSerializer):
    terminal_code = serializers.RegexField(r'^[A-Z0-9]{2,16}$')
    starting_serial = serializers.IntegerField(min_value=1, max_value=99999999)
    enrolled = serializers.SerializerMethodField()
    class Meta:
        model = FiscalTerminal
        fields = ['id', 'branch', 'terminal_code', 'machine_serial', 'min', 'ptu', 'ptu_issued_on', 'starting_serial', 'activated_at', 'enrolled']
        read_only_fields = ['id', 'activated_at']

    def get_enrolled(self, obj):
        return obj.installation_id is not None

    def validate_terminal_code(self, code):
        qs = FiscalTerminal.objects.filter(terminal_code=code)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError('Terminal code is already assigned.')
        return code

    def validate_ptu_issued_on(self, date):
        if date > timezone.localdate():
            raise ValidationError('Issue date cannot be in the future.')
        return date

    def validate(self, data):
        for key in ['machine_serial', 'min', 'ptu']:
            value = data.get(key, '').lower()
            if any(word in value for word in ['training', 'placeholder', 'configure']):
                raise ValidationError({key: 'Enter the actual registration details.'})
        return data


def audit(request, action, obj, before, after):
    FiscalAudit.objects.create(actor=request.user, action=action, entity_id=str(obj.pk), before=before, after=after)


def lock_settings():
    # All registration mutations serialize on the existing singleton, including
    # initial creation and claim retries. This also protects MySQL uniqueness checks.
    settings = StoreSettings.objects.select_for_update().get(pk=1)
    if not settings.setup_completed or not settings.business_id:
        raise ValidationError('Complete initial company setup first.')
    return settings


class FiscalSetupView(APIView):
    permission_classes = [FiscalAdmin]

    def get(self, request):
        company = FiscalCompany.objects.filter(pk=1).first()
        return Response({
            'business_id': StoreSettings.get_settings().business_id,
            'company': CompanySerializer(company).data if company else None,
            'branches': BranchSerializer(FiscalBranch.objects.select_related('branch').all(), many=True).data,
            'available_branches': list(Branch.objects.filter(active=True).values('id', 'code', 'name')),
            'terminals': TerminalSerializer(FiscalTerminal.objects.all(), many=True).data,
            'audit': list(FiscalAudit.objects.order_by('-id').values('id', 'actor__email', 'action', 'entity_id', 'created_at', 'before', 'after')[:100]),
        })

    @transaction.atomic
    def post(self, request):
        lock_settings()
        kind = request.data.get('kind')
        payload = request.data.get('data', {})
        if kind == 'company':
            obj = FiscalCompany.objects.filter(pk=1).first()
            cls = CompanySerializer
            if obj and obj.locked_at:
                raise ValidationError('Company identity is locked after terminal activation.')
        elif kind in ['branch', 'terminal']:
            model, cls = (FiscalBranch, BranchSerializer) if kind == 'branch' else (FiscalTerminal, TerminalSerializer)
            obj = None
            if request.data.get('id'):
                try:
                    obj = model.objects.get(pk=request.data['id'])
                except (model.DoesNotExist, ValueError, TypeError, DjangoValidationError):
                    raise ValidationError('Registration record was not found.')
            if obj and (obj.locked_at if kind == 'branch' else obj.activated_at):
                raise ValidationError('Activated registration details are locked.')
        else:
            raise ValidationError('Unknown registration action.')
        before = dict(cls(obj).data) if obj else {}
        serializer = cls(obj, data=payload)
        serializer.is_valid(raise_exception=True)
        obj = serializer.save(pk=1) if kind == 'company' and obj is None else serializer.save()
        audit(request, f'{kind}.saved', obj, before, dict(cls(obj).data))
        return Response(cls(obj).data)


class TerminalActivateView(APIView):
    permission_classes = [FiscalAdmin]

    @transaction.atomic
    def post(self, request, terminal_id):
        lock_settings()
        if not request.user.check_password(request.data.get('password', '')):
            raise PermissionDenied('Administrator password is incorrect.')
        if request.data.get('reviewed') is not True:
            raise ValidationError('Confirm the registration details and invoice series.')
        terminal = FiscalTerminal.objects.select_related('branch__branch').filter(pk=terminal_id).first()
        company = FiscalCompany.objects.filter(pk=1).first()
        if not terminal or not company:
            raise ValidationError('Save the company, branch and terminal details first.')
        if terminal.installation_id:
            raise ValidationError('This terminal is already enrolled. Its identity cannot be reassigned.')
        if not terminal.branch.branch.active:
            raise ValidationError('The assigned branch is inactive.')
        before = dict(TerminalSerializer(terminal).data)
        code = secrets.token_urlsafe(32)
        now = timezone.now()
        rotating = terminal.activated_at is not None
        terminal.activated_at = terminal.activated_at or now
        terminal.enrollment_hash = make_password(code)
        terminal.save()
        company.locked_at = company.locked_at or now
        company.save()
        terminal.branch.locked_at = terminal.branch.locked_at or now
        terminal.branch.save()
        audit(request, 'terminal.enrollment_code_rotated' if rotating else 'terminal.activated', terminal, before, dict(TerminalSerializer(terminal).data))
        return Response({'terminal_id': str(terminal.pk), 'enrollment_code': code})


class ClaimSerializer(serializers.Serializer):
    terminal_id = serializers.UUIDField()
    installation_id = serializers.UUIDField()
    local_terminal_id = serializers.UUIDField()
    enrollment_code = serializers.CharField(max_length=128)


class TerminalClaimView(APIView):
    permission_classes = [FiscalAdmin]

    @transaction.atomic
    def post(self, request):
        settings = lock_settings()
        s = ClaimSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        terminal = FiscalTerminal.objects.select_related('branch__branch', 'installation').filter(pk=d['terminal_id']).first()
        if not terminal or not terminal.activated_at or not check_password(d['enrollment_code'], terminal.enrollment_hash):
            raise PermissionDenied('Invalid terminal or enrollment code.')
        if not terminal.branch.branch.active:
            raise PermissionDenied('The assigned branch is inactive.')
        identity = str(d['installation_id'])
        local_terminal = str(d['local_terminal_id'])
        if terminal.installation_id:
            installation = terminal.installation
            if (installation.installation_id != identity or installation.terminal_id != local_terminal
                    or installation.authorized_staff_id != request.user.pk or not installation.is_active or not installation.sync_enabled):
                raise PermissionDenied('This terminal is already enrolled on another installation or is disabled.')
        else:
            if SyncInstallation.objects.filter(installation_id=identity).exists() or SyncInstallation.objects.filter(business_id=settings.business_id, terminal_id=local_terminal).exists():
                raise ValidationError('Installation identity is already in use.')
            terminal.installation = SyncInstallation.objects.create(
                business_id=settings.business_id, installation_id=identity,
                terminal_id=local_terminal, local_branch_id='branch-main',
                branch=terminal.branch.branch, authorized_staff=request.user,
                is_active=True, sync_enabled=True)
            terminal.save(update_fields=['installation'])
            audit(request, 'terminal.enrolled', terminal, {}, {'installation_id': identity, 'terminal_id': local_terminal})
        company = FiscalCompany.objects.get(pk=1)
        return Response({
            'companyId': identity, 'terminalId': local_terminal,
            'registeredName': company.registered_name, 'tin': company.tin,
            'address': terminal.branch.registered_address,
            'branchCode': terminal.branch.branch_code, 'rdo': terminal.branch.rdo,
            'registrationType': company.tax_type, 'terminalCode': terminal.terminal_code,
            'machineSerial': terminal.machine_serial, 'min': terminal.min, 'ptu': terminal.ptu,
            'ptuIssuedOn': terminal.ptu_issued_on.isoformat(), 'startingSerial': terminal.starting_serial,
            'cloudBusinessId': settings.business_id, 'cloudBranchCode': terminal.branch.branch.code,
            'serverTerminalId': str(terminal.pk), 'activatedAt': terminal.activated_at.isoformat(),
        })
