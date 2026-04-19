from odoo import api, fields, models
from odoo.exceptions import ValidationError


class BarcaMaintenancePlanLine(models.Model):
    _inherit = "barca.maintenance.plan.line"

    # Se mantiene opcional a nivel DB para no romper upgrades con líneas históricas.
    task_id = fields.Many2one(
        "barca.maintenance.task",
        string="Actividad",
    )
    frequency_km = fields.Float(string="Frecuencia km")
    frequency_days = fields.Integer(string="Frecuencia días")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("task_id"):
                raise ValidationError("Debe seleccionar una actividad para la línea del plan.")
        return super().create(vals_list)

    def write(self, vals):
        result = super().write(vals)
        if any(field in vals for field in ("task_id", "frequency_km", "frequency_days")):
            for rec in self:
                if (rec.frequency_km or rec.frequency_days) and not rec.task_id:
                    raise ValidationError(
                        "Debe seleccionar una actividad cuando define frecuencias en la línea del plan."
                    )
        return result
