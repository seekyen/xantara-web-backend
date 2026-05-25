from rest_framework.permissions import BasePermission

class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and getattr(request.user, 'role', None) == 'admin'

class IsAdminOrManager(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and getattr(request.user, 'role', None) in ('admin','manager')

class IsAdminOrManagerOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in ('GET','HEAD','OPTIONS'):
            return request.user.is_authenticated
        return request.user.is_authenticated and getattr(request.user, 'role', None) in ('admin','manager')
