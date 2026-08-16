from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

import pandas as pd

from core.models import (
    Company, Order, Machine, Quote, 
    QuoteLine, QuoteRevision, User,
    TelemetrySnapshot, MachineModel,
    MaintenanceTicket, OrderLine, Alarm
)




"""
    Our excel file which contains the data, has 12 sheets and each sheet
    is one of the tables.

    1. Companies            |       7. QuoteLines
    2. MachineModels        |       8. Orders
    3. Users                |       9. OrderLines
    4. Machines             |       10. Alarms
    5. Quotes               |       11. TelemetrySnapshots
    6. QuoteRevisions       |       12. MaintenanceTickets
    
"""


class Command(BaseCommand):

    help = "Import the AROL dataset from the Excel into the database"


    """
    python manage.py import_data --file path/to/data.xlsx
    """

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            required=True,
            help="Path to dataset .xlsx",
        )


    # What actually the commands do, after it is called
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



    def clean(self, value):

        """
            Convert Pandas NaN (empty cells) 
            
            into
             
            Python 'None' so it becomes a DB NULL.
        """
        if pd.isna(value):
            return None
        return value

    def make_aware(self, value):
            
            """
            1. Excel dates sometimes arrive as plain text not date objects

            2. Pandas internal date type isn't the same as Python

            3. Timezone-naive & Timezone=aware
            """

            value = self.clean(value)
            if value is None:
                return None

            
            # 1. if it arrived as text, parse it into a real datetime first.
            if isinstance(value, str):
                value = pd.to_datetime(value)

            # 2. pandas datetimes need converting to plain Python datetimes.
            if hasattr(value, "to_pydatetime"):
                value = value.to_pydatetime()

            # 3. attaches project's configured timezone (Europe/Rome) --> settings.py
            if timezone.is_naive(value):
                return timezone.make_aware(value)
            return value


    def import_companies(self, df):

        count = 0
        for _, row in df.iterrows(): # --> row, index inside df.iterrows
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
                user.set_password("arol1234") # --> It will hash the password
                user.save()
                count += 1

            self.stdout.write(self.style.SUCCESS(f"Imported {count} users"))


    def import_machines(self, df):

        count = 0
        for _, row in df.iterrows():
            Machine.objects.update_or_create(
                machine_id=row["machineId"],
                defaults={
                    "company": Company.objects.get(company_id=row["companyId"]),
                    "model": MachineModel.objects.get(model_id=row["modelId"]),
                    "serial_number": row["serialNumber"],
                    "delivery_date": self.clean(row["deliveryDate"]),
                    "plant_location": self.clean(row["plantLocation"]) or "",
                    "configuration_profile": self.clean(row["configurationProfile"]) or "",
                    "plc_family": self.clean(row["plcFamily"]) or "",
                    "software_version": self.clean(row["softwareVersion"]) or "",
                },
            )
            count += 1
        self.stdout.write(self.style.SUCCESS(f"Imported {count} machines"))



    def import_quotes(self, df):

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

        count = 0
        for _, row in df.iterrows():

            """
                This is one of the edge cases:
                    A QuoteLine or MaintenanceTicke with no machine/alarm attached
            """

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



    def import_alarms(self, df):

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

        # Cache machines so we don't hit the DB on every one of the ~5,760 rows.
        """
            The sheet has ~5,760 rows, doing a separate database query for every single row
            (like the other methods do) would be slow.
            
            Instead, this line loads all machines into memory once,
            into a dictionary keyed by ID, before the loop starts.
             
            Then inside the loop, machines[row["machineId"]] is an instant lookup in memory
        """
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