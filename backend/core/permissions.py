from rest_framework.permissions import BasePermission



"""
    A permission decides, wether a particular user is 
    allowed to ask for some specific data or not 

    'has_permission' is the method which is called
    automatically on all the sended requests.
"""

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