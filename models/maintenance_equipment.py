from odoo import fields, models


class MaintenanceEquipment(models.Model):
    _inherit = "maintenance.equipment"

    vehicle_id = fields.Many2one(
        "fleet.vehicle",
        string="Vehículo",
        ondelete="cascade",
    )
    x_odometer_last_service = fields.Float(
        string="Odómetro último servicio",
        related="vehicle_id.x_odometer_last_service",
        readonly=True,
    )
    x_hours_last_service = fields.Float(
        string="Horas operación último servicio",
        related="vehicle_id.x_hours_last_service",
        readonly=True,
    )
    x_last_entry_date = fields.Date(
        string="Última entrada a taller",
        related="vehicle_id.x_last_entry_date",
        readonly=True,
    )
    x_last_exit_date = fields.Date(
        string="Última salida a taller",
        related="vehicle_id.x_last_exit_date",
        readonly=True,
    )
    x_current_odometer = fields.Float(
        string="Último odómetro",
        related="vehicle_id.odometer",
        readonly=True,
    )
    x_current_operating_hours = fields.Float(
        string="Horas de operación",
        related="vehicle_id.x_operating_hours",
        readonly=True,
    )

    x_doc_circulation_permit_expiry = fields.Date(
        string="Vencimiento permiso de circulación",
        related="vehicle_id.x_doc_circulation_permit_expiry",
        readonly=True,
    )
    x_doc_technical_review_expiry = fields.Date(
        string="Vencimiento revisión técnica",
        related="vehicle_id.x_doc_technical_review_expiry",
        readonly=True,
    )
    x_doc_fuel_card = fields.Char(
        string="Tarjeta combustible",
        related="vehicle_id.x_doc_fuel_card",
        readonly=True,
    )
    x_doc_tag = fields.Boolean(
        string="TAG",
        related="vehicle_id.x_doc_tag",
        readonly=True,
    )
    x_alert_days_before = fields.Integer(
        string="Días alerta vencimiento",
        related="vehicle_id.x_alert_days_before",
        readonly=True,
    )

    _sql_constraints = [
        (
            "unique_vehicle_equipment",
            "unique(vehicle_id)",
            "Ya existe un equipo de mantenimiento para este vehículo.",
        )
    ]
