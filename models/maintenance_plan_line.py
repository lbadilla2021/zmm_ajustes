from odoo import fields, models


class BarcaMaintenancePlanLine(models.Model):
    _inherit = "barca.maintenance.plan.line"

    # Se mantiene opcional a nivel DB para no romper upgrades con líneas históricas.
    # La obligatoriedad se aplica en la vista editable de planes.
    task_id = fields.Many2one(
        "barca.maintenance.task",
        string="Actividad",
    )
    frequency_km = fields.Float(string="Frecuencia km")
    frequency_days = fields.Integer(string="Frecuencia días")
