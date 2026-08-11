from rest_framework.permissions import BasePermission

class CanSeeOperational(BasePermission):
    """
        Only 'full & technician' see telemetry, alarms, maintenance
    """

    message = "Your access level does not permit operatioinal data."

    def has_permission(self, request, view):
        return request.user.visibility in ("full", "technician")

class CanSeeCommercial(BasePermission):
    """
        Only 'full & 'commercial' see quotes and orders.
    """
    
    message = "Your access level does not permit commercial data."

    def has_permission(self, request, view):
        return request.user.visibility in ("full", "commercial")