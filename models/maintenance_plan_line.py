from odoo import fields, models


class BarcaMaintenancePlanLine(models.Model):
    _inherit = "barca.maintenance.plan.line"

    task_id = fields.Many2one(
        "barca.maintenance.task",
        string="Actividad",
        required=True,
    )
    frequency_km = fields.Float(string="Frecuencia km")
    frequency_days = fields.Integer(string="Frecuencia días")
