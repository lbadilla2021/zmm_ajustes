from odoo import fields, models


class FleetVehicleLogServices(models.Model):
    _inherit = "fleet.vehicle.log.services"

    # Compatibilidad Odoo 18 para vistas/filtros que usan `name` en costos/servicios
    name = fields.Char(string="Nombre")