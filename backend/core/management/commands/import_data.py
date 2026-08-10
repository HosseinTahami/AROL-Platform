import pandas as pd
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Import the AROL dataset from the Excel workbook into the database"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            required=True,
            help="Path to the AROL dataset .xlsx workbook",
        )

    def handle(self, *args, **options):
        file_path = options["file"]
        self.stdout.write(f"Reading workbook: {file_path}")

        try:
            workbook = pd.read_excel(file_path, sheet_name=None)
        except FileNotFoundError:
            raise CommandError(f"File not found: {file_path}")

        # Import in dependency order (things pointed at come first).
        self.import_companies(workbook["Companies"])
        self.import_machine_models(workbook["MachineModels"])
        self.import_users(workbook["Users"])
        self.import_machines(workbook["Machines"])
        self.import_quotes(workbook["Quotes"])
        self.import_quote_revisions(workbook["QuoteRevisions"])
        self.import_quote_lines(workbook["QuoteLines"])
        self.import_orders(workbook["Orders"])
        self.import_order_lines(workbook["OrderLines"])
        self.import_alarms(workbook["Alarms"])
        self.import_telemetry(workbook["TelemetrySnapshots"])
        self.import_maintenance_tickets(workbook["MaintenanceTickets"])

        self.stdout.write(self.style.SUCCESS("Import complete."))

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def clean(self, value):
        """Convert pandas NaN (empty cell) into None so it becomes a DB NULL."""
        if pd.isna(value):
            return None
        return value

    def make_aware(self, value):
            """Turn a timestamp cell into a timezone-aware datetime; pass through None."""
            from django.utils import timezone
            value = self.clean(value)
            if value is None:
                return None
            # If it arrived as text, parse it into a real datetime first.
            if isinstance(value, str):
                value = pd.to_datetime(value)
            # pandas datetimes need converting to plain Python datetimes.
            if hasattr(value, "to_pydatetime"):
                value = value.to_pydatetime()
            if timezone.is_naive(value):
                return timezone.make_aware(value)
            return value

    # ------------------------------------------------------------------ #
    # Identity
    # ------------------------------------------------------------------ #

    def import_companies(self, df):
        from core.models import Company

        count = 0
        for _, row in df.iterrows():
            Company.objects.update_or_create(
                company_id=row["companyId"],
                defaults={
                    "company_name": row["companyName"],
                    "country": row["country"],
                    "city": row["city"],
                    "sector": row["sector"],
                    "currency": row["currency"],
                    "locale": row["locale"],
                },
            )
            count += 1
        self.stdout.write(self.style.SUCCESS(f"Imported {count} companies"))

    def import_machine_models(self, df):
        from core.models import MachineModel

        count = 0
        for _, row in df.iterrows():
            MachineModel.objects.update_or_create(
                model_id=row["modelId"],
                defaults={
                    "model_code": row["modelCode"],
                    "description": row["description"],
                    "primitive_diameter": self.clean(row["primitiveDiameter"]),
                    "nominal_heads": self.clean(row["nominalHeads"]),
                    "container_type": row["containerType"],
                    "cap_type": row["capType"],
                    "industry_segment": row["industrySegment"],
                    "notes": row["notes"],
                },
            )
            count += 1
        self.stdout.write(self.style.SUCCESS(f"Imported {count} machine models"))

    def import_users(self, df):
            from core.models import User, Company

            count = 0
            for _, row in df.iterrows():
                user, _ = User.objects.update_or_create(
                    user_id=row["userId"],
                    defaults={
                        "username": row["email"],
                        "company": Company.objects.get(company_id=row["companyId"]),
                        "first_name": row["firstName"],
                        "last_name": row["lastName"],
                        "email": row["email"],
                        "job_title": row["jobTitle"],
                        "visibility": row["visibility"],
                    },
                )
                user.set_password("arol1234")
                user.save()
                count += 1
            self.stdout.write(self.style.SUCCESS(f"Imported {count} users"))

    def import_machines(self, df):
        from core.models import Machine, Company, MachineModel

        count = 0
        for _, row in df.iterrows():
            Machine.objects.update_or_create(
                machine_id=row["machineId"],
                defaults={
                    "company": Company.objects.get(company_id=row["companyId"]),
                    "model": MachineModel.objects.get(model_id=row["modelId"]),
                    "serial_number": row["serialNumber"],
                    "delivery_date": self.clean(row["deliveryDate"]),
                    "plant_location": row["plantLocation"],
                    "configuration_profile": row["configurationProfile"],
                    "plc_family": row["plcFamily"],
                    "software_version": row["softwareVersion"],
                },
            )
            count += 1
        self.stdout.write(self.style.SUCCESS(f"Imported {count} machines"))

    # ------------------------------------------------------------------ #
    # Commercial
    # ------------------------------------------------------------------ #

    def import_quotes(self, df):
        from core.models import Quote, Company

        count = 0
        for _, row in df.iterrows():
            Quote.objects.update_or_create(
                quote_id=row["quoteId"],
                defaults={
                    "company": Company.objects.get(company_id=row["companyId"]),
                    "currency": row["currency"],
                    "created_at": self.clean(row["createdAt"]),
                    "valid_until": self.clean(row["validUntil"]),
                    "description": row["description"],
                },
            )
            count += 1
        self.stdout.write(self.style.SUCCESS(f"Imported {count} quotes"))

    def import_quote_revisions(self, df):
        from core.models import QuoteRevision, Quote

        count = 0
        for _, row in df.iterrows():
            QuoteRevision.objects.update_or_create(
                quote_revision_id=row["quoteRevisionId"],
                defaults={
                    "quote": Quote.objects.get(quote_id=row["quoteId"]),
                    "revision_number": row["revisionNumber"],
                    "revision_status": row["revisionStatus"],
                    "issued_at": self.clean(row["issuedAt"]),
                    "discount_rate": row["discountRate"],
                    "change_summary": row["changeSummary"],
                },
            )
            count += 1
        self.stdout.write(self.style.SUCCESS(f"Imported {count} quote revisions"))

    def import_quote_lines(self, df):
        from core.models import QuoteLine, QuoteRevision, Machine

        count = 0
        for _, row in df.iterrows():
            machine_id = self.clean(row["machineId"])
            machine = Machine.objects.get(machine_id=machine_id) if machine_id else None
            QuoteLine.objects.update_or_create(
                quote_line_id=row["quoteLineId"],
                defaults={
                    "quote_revision": QuoteRevision.objects.get(
                        quote_revision_id=row["quoteRevisionId"]
                    ),
                    "machine": machine,
                    "price": self.clean(row["price"]),
                    "description": row["description"],
                },
            )
            count += 1
        self.stdout.write(self.style.SUCCESS(f"Imported {count} quote lines"))

    def import_orders(self, df):
        from core.models import Order, Quote, Company

        count = 0
        for _, row in df.iterrows():
            Order.objects.update_or_create(
                order_id=row["orderId"],
                defaults={
                    "quote": Quote.objects.get(quote_id=row["quoteId"]),
                    "company": Company.objects.get(company_id=row["companyId"]),
                    "order_status": row["orderStatus"],
                    "order_date": self.clean(row["orderDate"]),
                    "expected_delivery_date": self.clean(row["expectedDeliveryDate"]),
                    "shipment_status": row["shipmentStatus"],
                    "currency": row["currency"],
                    "notes": row["notes"],
                },
            )
            count += 1
        self.stdout.write(self.style.SUCCESS(f"Imported {count} orders"))

    def import_order_lines(self, df):
        from core.models import OrderLine, Order

        count = 0
        for _, row in df.iterrows():
            OrderLine.objects.update_or_create(
                order_line_id=row["orderLineId"],
                defaults={
                    "order": Order.objects.get(order_id=row["orderId"]),
                    "fulfillment_status": row["fulfillmentStatus"],
                },
            )
            count += 1
        self.stdout.write(self.style.SUCCESS(f"Imported {count} order lines"))

    # ------------------------------------------------------------------ #
    # Operational
    # ------------------------------------------------------------------ #

    def import_alarms(self, df):
        from core.models import Alarm, Machine

        count = 0
        for _, row in df.iterrows():
            Alarm.objects.update_or_create(
                alarm_id=row["alarmId"],
                defaults={
                    "machine": Machine.objects.get(machine_id=row["machineId"]),
                    "timestamp": self.make_aware(row["timestamp"]),
                    "alarm_code": row["alarmCode"],
                    "severity": row["severity"],
                    "alarm_status": row["alarmStatus"],
                },
            )
            count += 1
        self.stdout.write(self.style.SUCCESS(f"Imported {count} alarms"))

    def import_telemetry(self, df):
        from core.models import TelemetrySnapshot, Machine

        # Cache machines so we don't hit the DB on every one of the ~5,760 rows.
        machines = {m.machine_id: m for m in Machine.objects.all()}

        count = 0
        for _, row in df.iterrows():
            TelemetrySnapshot.objects.update_or_create(
                telemetry_id=row["telemetryId"],
                defaults={
                    "machine": machines[row["machineId"]],
                    "timestamp": self.make_aware(row["timestamp"]),                    "operational_status": row["operationalStatus"],
                    "production_rate_bph": self.clean(row["productionRateBph"]),
                    "uptime_percentage": self.clean(row["uptimePercentage"]),
                    "alarm_count": self.clean(row["alarmCount"]) or 0,
                    "temperature_c": self.clean(row["temperatureC"]),
                    "energy_kwh": self.clean(row["energyKwh"]),
                    "health_note": self.clean(row["healthNote"]) or "",
                },
            )
            count += 1
        self.stdout.write(self.style.SUCCESS(f"Imported {count} telemetry snapshots"))

    def import_maintenance_tickets(self, df):
        from core.models import MaintenanceTicket, Machine, Alarm

        count = 0
        for _, row in df.iterrows():
            alarm_id = self.clean(row["alarmId"])
            alarm = Alarm.objects.get(alarm_id=alarm_id) if alarm_id else None
            MaintenanceTicket.objects.update_or_create(
                ticket_id=row["ticketId"],
                defaults={
                    "machine": Machine.objects.get(machine_id=row["machineId"]),
                    "alarm": alarm,
                    "ticket_type": row["ticketType"],
                    "ticket_status": row["ticketStatus"],
                    "priority": row["priority"],
                    "created_date": self.clean(row["createdDate"]),
                    "owner_role": row["ownerRole"],
                },
            )
            count += 1
        self.stdout.write(self.style.SUCCESS(f"Imported {count} maintenance tickets"))