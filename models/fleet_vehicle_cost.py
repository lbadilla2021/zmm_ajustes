from odoo import fields, models


class FleetVehicleCost(models.Model):
    _inherit = "fleet.vehicle.cost"

    # Compatibilidad para vistas/filtros que usan `name` en costos/servicios
    name = fields.Char(string="Nombre")
