from odoo import fields, models


class FleetVehicleLogServices(models.Model):
    _inherit = "fleet.vehicle.log.services"

    # Campo de compatibilidad para vistas de búsqueda que esperan `name`
    name = fields.Char(string="Nombre")
