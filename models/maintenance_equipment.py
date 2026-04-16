from odoo import fields, models


class MaintenanceEquipment(models.Model):
    _inherit = "maintenance.equipment"

    vehicle_id = fields.Many2one(
        "fleet.vehicle",
        string="Vehículo",
        ondelete="cascade",
    )

    _sql_constraints = [
        (
            "unique_vehicle_equipment",
            "unique(vehicle_id)",
            "Ya existe un equipo de mantenimiento para este vehículo.",
        )
    ]
