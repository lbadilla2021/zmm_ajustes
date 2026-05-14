import re

from odoo import api, fields, models
from odoo.tools import html_escape


class FleetVehicle(models.Model):
    _inherit = "fleet.vehicle"

    # Identificación
    x_internal_code = fields.Char(
        string="Código interno",
        compute="_compute_internal_code",
        store=True,
        readonly=True,
    )
    x_engine_code = fields.Char(string="Número de Motor")

    # Medición
    x_odometer_last_service = fields.Float(string="Odómetro último servicio")
    x_odometer_next_service = fields.Float(
        string="Próximo servicio (km)",
        compute="_compute_next_service",
        store=True,
    )
    x_operating_hours = fields.Float(string="Horas de operación")
    x_hours_last_service = fields.Float(
        string="Horas operación último servicio",
        help="Horas de operación registradas al momento del último servicio realizado.",
    )

    # Taller
    x_last_entry_date = fields.Date(string="Última entrada a taller")
    x_last_exit_date = fields.Date(string="Última salida a taller")
    x_downtime_total = fields.Float(
        string="Tiempo fuera de servicio (hrs)",
        compute="_compute_downtime",
        store=True,
    )

    # Documentación
    x_doc_circulation_permit_expiry = fields.Date(
        string="Vencimiento permiso de circulación"
    )
    x_doc_technical_review_expiry = fields.Date(
        string="Vencimiento revisión técnica"
    )
    x_doc_padron = fields.Char(string="Padrón")
    x_doc_fuel_card = fields.Char(string="Tarjeta combustible")
    x_doc_tag = fields.Boolean(string="TAG")
    x_alert_days_before = fields.Integer(string="Días alerta vencimiento", default=15)
    x_has_insurance_contract = fields.Boolean(
        string="Seguro",
        compute="_compute_has_insurance_contract",
        readonly=True,
    )

    # Notas
    x_maintenance_note = fields.Text(string="Notas de mantención")

    @api.depends("license_plate")
    def _compute_internal_code(self):
        for vehicle in self:
            digits = "".join(re.findall(r"\d", vehicle.license_plate or ""))
            vehicle.x_internal_code = digits[-2:] if len(digits) >= 2 else False

    @api.depends("x_odometer_last_service")
    def _compute_next_service(self):
        for vehicle in self:
            vehicle.x_odometer_next_service = vehicle.x_odometer_last_service + 5000.0

    @api.depends("x_last_entry_date", "x_last_exit_date")
    def _compute_downtime(self):
        for vehicle in self:
            vehicle.x_downtime_total = 0.0

    @api.depends("log_contracts.cost_subtype_id")
    def _compute_has_insurance_contract(self):
        contracts_data = self.env["fleet.vehicle.log.contract"].with_context(
            active_test=False
        )._read_group(
            [
                ("vehicle_id", "in", self.ids),
                ("cost_subtype_id.name", "ilike", "seguro"),
            ],
            ["vehicle_id"],
            ["__count"],
        )
        vehicle_ids_with_insurance = {
            vehicle.id for vehicle, count in contracts_data if count
        }

        for vehicle in self:
            vehicle.x_has_insurance_contract = (
                vehicle.id in vehicle_ids_with_insurance
            )

    def _send_documentation_change_email(self, initial_values, written_values):
        field_labels = {
            "x_doc_fuel_card": self._fields["x_doc_fuel_card"].string,
            "x_doc_tag": self._fields["x_doc_tag"].string,
        }
        changes_by_vehicle = []

        for vehicle in self:
            vehicle_changes = []
            for field_name, label in field_labels.items():
                if field_name not in written_values:
                    continue
                previous_value = initial_values[vehicle.id][field_name]
                current_value = vehicle[field_name]
                if (previous_value or False) == (current_value or False):
                    continue
                vehicle_changes.append(
                    "%s: %s → %s"
                    % (
                        label,
                        previous_value or "Sin valor",
                        current_value or "Sin valor",
                    )
                )

            if vehicle_changes:
                changes_by_vehicle.append((vehicle, vehicle_changes))

        if not changes_by_vehicle:
            return

        recipients = self.env["barca.fleet.alert.rule"]._get_recipients_for_rule(
            "Modificaciones"
        )
        if not recipients:
            return

        body_parts = [
            "<p>Se registraron modificaciones en documentación de vehículos:</p>",
            "<ul>",
        ]
        for vehicle, vehicle_changes in changes_by_vehicle:
            body_parts.append(
                "<li><strong>%s</strong><ul>" % html_escape(vehicle.display_name)
            )
            for change in vehicle_changes:
                body_parts.append("<li>%s</li>" % html_escape(change))
            body_parts.append("</ul></li>")
        body_parts.append("</ul>")

        email_from = (
            self.env.user.email_formatted
            or self.env.company.email_formatted
            or "no-reply@example.com"
        )
        self.env["mail.mail"].sudo().create(
            {
                "subject": "Modificaciones de documentación de vehículos",
                "body_html": "".join(body_parts),
                "email_from": email_from,
                "email_to": ", ".join(recipients),
                "auto_delete": False,
            }
        ).send()

    @api.model_create_multi
    def create(self, vals_list):
        vehicles = super().create(vals_list)
        equipment_model = self.env["maintenance.equipment"]

        existing_equipment = equipment_model.search(
            [("vehicle_id", "in", vehicles.ids)]
        ).mapped("vehicle_id")
        vehicles_without_equipment = vehicles - existing_equipment

        equipment_to_create = [
            {
                "name": vehicle.name,
                "vehicle_id": vehicle.id,
            }
            for vehicle in vehicles_without_equipment
        ]
        if equipment_to_create:
            equipment_model.create(equipment_to_create)

        return vehicles

    def write(self, vals):
        watched_fields = {"x_doc_fuel_card", "x_doc_tag"}
        initial_values = {}
        if watched_fields.intersection(vals):
            initial_values = {
                vehicle.id: {
                    field_name: vehicle[field_name]
                    for field_name in watched_fields
                }
                for vehicle in self
            }

        res = super().write(vals)

        if "name" in vals:
            equipment_model = self.env["maintenance.equipment"]
            for rec in self:
                equipment = equipment_model.search(
                    [("vehicle_id", "=", rec.id)], limit=1
                )
                if equipment:
                    equipment.name = rec.name

        if initial_values:
            self._send_documentation_change_email(initial_values, vals)

        return res
