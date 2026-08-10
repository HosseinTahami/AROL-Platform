from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):

    VISIBILITY_FULL = "full"
    VISIBILITY_TECHNICIAN = "technician"
    VISIBILITY_COMMERCIAL = "commercial"

    VISIBILITY_CHOICES = [
        (VISIBILITY_FULL, "Full"),
        (VISIBILITY_TECHNICIAN, "Technician"),
        (VISIBILITY_COMMERCIAL, "Commercial"),
    ]

    company = models.ForeignKey(
        "Company",
        on_delete=models.CASCADE,
        related_name="users",
        null=True,
        blank=True
    )

    job_title = models.CharField(max_length=128, blank=True)

    visibility = models.CharField(
        max_length=32,
        choices=VISIBILITY_CHOICES,
        default=VISIBILITY_TECHNICIAN
    )

    def __str__(self):
        return self.username


class Company(models.Model):

    company_id = models.CharField(max_length=64, primary_key=True)
    company_name = models.CharField(max_length=128)
    country = models.CharField(max_length=128)
    city = models.CharField(max_length=128)
    sector = models.CharField(max_length=128)
    currency = models.CharField(max_length=8)
    locale = models.CharField(max_length=32)

    class Meta:
        verbose_name_plural = "Companies"


    def __str__(self):
        return self.company_name



class MachineModel(models.Model):

    model_id = models.CharField(max_length=64, primary_key=True)
    model_code = models.CharField(max_length=64)
    description = models.CharField(max_length=256, blank=True)
    primitive_diameter = models.FloatField(null=True, blank=True)
    cap_type = models.CharField(max_length=128, blank=True)
    container_type = models.CharField(max_length=128, blank=True)
    nominal_heads = models.IntegerField(null=True, blank=True)
    notes = models.TextField(blank=True)
    industry_segment = models.CharField(max_length=128, blank=True)

    def __str__(self):
        return f"{self.model_code} | {self.model_id}"

    class Meta:
        verbose_name_plural = "Machine Models"


class Machine(models.Model):

    PLC_SIEMENS = "SIEMENS-SIMATIC-S7"
    PLC_LINE_INTEGRATED = "LINE-PLC-INTEGRATED"
    PLC_HARDWIRED = "HARDWIRED-CONTROL-PANEL"

    PLC_FAMILY_CHOICES = [
        (PLC_SIEMENS, "Siemens Simatic S7"),
        (PLC_LINE_INTEGRATED, "Line PLC Integrated"),
        (PLC_HARDWIRED, "Hardwired Control Panel"),
    ]

    machine_id = models.CharField(max_length=64, primary_key=True)

    company = models.ForeignKey(
        "Company",
        on_delete=models.CASCADE,
        related_name="machines"
    )

    model = models.ForeignKey(
        "MachineModel",
        on_delete=models.PROTECT,
        related_name="machines"
    )

    serial_number = models.CharField(max_length=64, unique=True)
    delivery_date = models.DateField(null=True, blank=True)
    plant_location = models.CharField(max_length=256, blank=True)
    configuration_profile = models.TextField(blank=True)

    plc_family = models.CharField(
        max_length=32, 
        choices=PLC_FAMILY_CHOICES,
        blank=True
    )

    software_version = models.CharField(max_length=64, blank=True)

    def __str__(self):
        return f"{self.serial_num} | {self.machine_id}"



class Alarm(models.Model):

    SEVERITY_CRITICAL = "Critical"
    SEVERITY_HIGH = "High"
    SEVERITY_MEDIUM = "Medium"
    SEVERITY_LOW = "Low"
    SEVERITY_CHOICES = [
        (SEVERITY_CRITICAL, "Critical"),
        (SEVERITY_HIGH, "High"),
        (SEVERITY_MEDIUM, "Medium"),
        (SEVERITY_LOW, "Low"),
    ]


    STATUS_OPEN = "Open"
    STATUS_ACKNOWLEDGED = "Acknowledged"
    STATUS_RESOLVED = "Resolved"
    STATUS_CHOICES = [
        (STATUS_OPEN, "Open"),
        (STATUS_ACKNOWLEDGED, "Acknowledged"),
        (STATUS_RESOLVED, "Resolved"),
    ]

    alarm_id = models.CharField(max_length=64, primary_key=True)
    machine = models.ForeignKey(
        "Machine",
        on_delete=models.CASCADE,
        related_name="alarms"
    )


    timestamp = models.DateTimeField()
    alarm_code = models.CharField(max_length=64)
    severity = models.CharField(max_length=16, choices=SEVERITY_CHOICES)
    alarm_status = models.CharField(max_length=16, choices=STATUS_CHOICES)

    def __str__(self):
        return f"{self.alarm_code} from {self.machine_id}"


class MaintenanceTicket(models.Model):

    TYPE_REMOTE = "Remote troubleshooting"
    TYPE_ONSITE = "On-site service"
    TYPE_SCHEDULED = "Scheduled maintenance"
    TYPE_OVERHAUL = "Overhaul"
    TYPE_SIZE_CHANGE = "Size change assistance"
    TYPE_SPARE_PARTS = "Spare parts request"

    TYPE_CHOICES = [
        (TYPE_REMOTE, "Remote Troubleshooting"),
        (TYPE_ONSITE, "On-site Service"),
        (TYPE_SPARE_PARTS, "Spare Parts Request"),
        (TYPE_SCHEDULED, "Scheduled Maintenance"),
        (TYPE_OVERHAUL, "Overhaul"),
        (TYPE_SIZE_CHANGE, "Size Change Assistance"),
    ]



    STATUS_OPEN = "Open"
    STATUS_IN_PROGRESS = "In progress"
    STATUS_WAITING_PARTS = "Waiting for parts"
    STATUS_RESOLVED = "Resolved"
    STATUS_CLOSED = "Closed"
    STATUS_CHOICES = [
        (STATUS_OPEN, "Open"),
        (STATUS_IN_PROGRESS, "In progress"),
        (STATUS_WAITING_PARTS, "Waiting for parts"),
        (STATUS_RESOLVED, "Resolved"),
        (STATUS_CLOSED, "Closed"),
    ]


    PRIORITY_CRITICAL = "Critical"
    PRIORITY_HIGH = "High"
    PRIORITY_MEDIUM = "Medium"
    PRIORITY_LOW = "Low"
    PRIORITY_CHOICES = [
        (PRIORITY_CRITICAL, "Critical"),
        (PRIORITY_HIGH, "High"),
        (PRIORITY_MEDIUM, "Medium"),
        (PRIORITY_LOW, "Low"),
    ]

    ROLE_LINE_OPERATOR = "Line Operator"
    ROLE_MAINTENANCE_MAN = "Maintenance Man"
    ROLE_PLANT_MANAGER = "Plant Maintenance Manager"
    ROLE_AROL_SERVICE = "AROL Technical Service"
    OWNER_ROLE_CHOICES = [
        (ROLE_LINE_OPERATOR, "Line Operator"),
        (ROLE_MAINTENANCE_MAN, "Maintenance Man"),
        (ROLE_PLANT_MANAGER, "Plant Maintenance Manager"),
        (ROLE_AROL_SERVICE, "AROL Technical Service"),
    ]


    ticket_id = models.CharField(max_length=64, primary_key=True)
    machine = models.ForeignKey(
        "Machine",
        on_delete=models.CASCADE,
        related_name = "maintenance_tickets",
    )

    alarm = models.ForeignKey(
        "Alarm",
        on_delete=models.SET_NULL,
        related_name="maintenance_tickets",
        null=True,
        blank=True
    )

    ticket_type = models.CharField(max_length=32, choices=TYPE_CHOICES)
    ticket_status = models.CharField(max_length=32, choices=STATUS_CHOICES)
    priority = models.CharField(max_length=16, choices=PRIORITY_CHOICES)
    created_date = models.DateField(null=True, blank=True)
    owner_role = models.CharField(max_length=32, choices=OWNER_ROLE_CHOICES)

    def __str__(self):
        return f"{self.ticket_id} | {self.ticket_status}"


class TelemetrySnapshot(models.Model):

    STATUS_RUNNING = "Running"
    STATUS_ALARM = "Alarm"
    STATUS_IDLE = "Idle"
    STATUS_STOPPED = "Stopped"
    STATUS_MAINTENANCE = "Maintenance"
    STATUS_SIZE_CHANGE = "Size change"
    OPERATIONAL_STATUS_CHOICES = [
        (STATUS_RUNNING, "Running"),
        (STATUS_ALARM, "Alarm"),
        (STATUS_IDLE, "Idle"),
        (STATUS_STOPPED, "Stopped"),
        (STATUS_MAINTENANCE, "Maintenance"),
        (STATUS_SIZE_CHANGE, "Size change"),
    ]


    telemetry_id = models.CharField(max_length=64, primary_key=True)
    machine = models.ForeignKey(
        "Machine",
        on_delete=models.CASCADE,
        related_name="telemetry_snapshots",
    )

    timestamp = models.DateTimeField()
    operational_status = models.CharField(
        max_length=16,
        choices=OPERATIONAL_STATUS_CHOICES,
    )

    production_rate_bph = models.FloatField(null=True, blank=True)
    uptime_percentage = models.FloatField(null=True, blank=True)
    alarm_count = models.IntegerField(default=0)
    temperature_c = models.FloatField(null=True, blank=True)
    energy_kwh = models.FloatField(null=True, blank=True)
    health_note = models.TextField(blank=True)

    def __str__(self):
        return f"{self.machine_id} ---> {self.timestamp}"


class Quote(models.Model):
    quote_id = models.CharField(max_length=64, primary_key=True)
    company = models.ForeignKey(
        "Company",
        on_delete=models.CASCADE,
        related_name="quotes"
    )

    currency = models.CharField(max_length=8)
    created_at = models.DateField(null=True, blank=True)
    valid_until = models.DateField(null=True, blank=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.quote_id} | {self.company_id}"

class QuoteRevision(models.Model):

    STATUS_DRAFT = "Draft"
    STATUS_SUBMITTED = "Submitted"
    STATUS_SUPERSEDED = "Superseded"
    STATUS_APPROVED = "Approved"
    STATUS_REJECTED = "Rejected"
    STATUS_EXPIRED = "Expired"
    REVISION_STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_SUBMITTED, "Submitted"),
        (STATUS_SUPERSEDED, "Superseded"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_REJECTED, "Rejected"),
        (STATUS_EXPIRED, "Expired"),
    ]

    quote_revision_id = models.CharField(
        max_length=64,
        primary_key=True
    )

    quote = models.ForeignKey(
        "Quote",
        on_delete=models.CASCADE,
        related_name="revisions"
    )

    revision_number = models.IntegerField()

    revision_status = models.CharField(
        max_length=16,
        choices=REVISION_STATUS_CHOICES
    )

    issued_at = models.DateField(null=True, blank=True)
    discount_rate = models.FloatField(default=0)
    change_summary = models.TextField(blank=True)


    def __str__(self):
        return f"{self.quote_id} rev {self.revision_number} | {self.revision_status}"


class QuoteLine(models.Model):

    quote_line_id = models.CharField(max_length=64, primary_key=True)
    quote_revision = models.ForeignKey(
        "QuoteRevision",
        on_delete=models.CASCADE,
        related_name="lines",
    )

    machine = models.ForeignKey(
        "Machine",
        on_delete=models.SET_NULL,
        related_name="quote_lines",
        null=True,
        blank=True,
    )

    price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.quote_line_id} | {self.quote_revision_id}s"


class Order(models.Model):


    ORDER_CONFIRMED = "Confirmed"
    ORDER_IN_PRODUCTION = "In production"
    ORDER_DELIVERED = "Delivered"
    ORDER_CLOSED = "Closed"
    ORDER_STATUS_CHOICES = [
        (ORDER_CONFIRMED, "Confirmed"),
        (ORDER_IN_PRODUCTION, "In production"),
        (ORDER_DELIVERED, "Delivered"),
        (ORDER_CLOSED, "Closed"),
    ]

    SHIPMENT_IN_PRODUCTION = "In production"
    SHIPMENT_READY = "Ready for shipment"
    SHIPMENT_DELIVERED = "Delivered"
    SHIPMENT_INSTALLED = "Installed"
    SHIPMENT_STATUS_CHOICES = [
        (SHIPMENT_IN_PRODUCTION, "In production"),
        (SHIPMENT_READY, "Ready for shipment"),
        (SHIPMENT_DELIVERED, "Delivered"),
        (SHIPMENT_INSTALLED, "Installed"),
    ]


    order_id = models.CharField(max_length=64, primary_key=True)
    quote = models.ForeignKey(
        "Quote",
        on_delete=models.PROTECT,
        related_name="orders"
    )

    company = models.ForeignKey(
        "Company",
        on_delete=models.CASCADE,
        related_name="orders"
    )

    order_status = models.CharField(max_length=16, choices=ORDER_STATUS_CHOICES)
    order_date = models.DateField(null=True, blank=True)
    expected_delivery_date = models.DateField(null=True, blank=True)
    shipment_status = models.CharField(
        max_length=20,
        choices=SHIPMENT_STATUS_CHOICES
    )

    currency = models.CharField(max_length=8)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.order_id} | {self.order_status}"


class OrderLine(models.Model):

    FULFILLMENT_MANUFACTURING = "Manufacturing"
    FULFILLMENT_READY = "Ready for shipment"
    FULFILLMENT_DELIVERED = "Delivered"
    FULFILLMENT_STATUS_CHOICES = [
        (FULFILLMENT_MANUFACTURING, "Manufacturing"),
        (FULFILLMENT_READY, "Ready for shipment"),
        (FULFILLMENT_DELIVERED, "Delivered"),
    ]

    order_line_id = models.CharField(max_length=64, primary_key=True)
    order = models.ForeignKey(
        "Order",
        on_delete=models.CASCADE,
        related_name="lines"
    )

    fulfillment_status = models.CharField(
        max_length=20,
        choices=FULFILLMENT_STATUS_CHOICES
    )

    def __str__(self):
        return f"{self.order_line_id} | {self.fulfillment_status}"