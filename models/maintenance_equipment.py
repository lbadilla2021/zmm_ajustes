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

    _sql_constraints = [
        (
            "unique_vehicle_equipment",
            "unique(vehicle_id)",
            "Ya existe un equipo de mantenimiento para este vehículo.",
        )
    ]
