from odoo import fields, models


class BarcaInterventionType(models.Model):
    _name = "barca.intervention.type"
    _description = "Tipo de intervención"

    name = fields.Char(string="Nombre", required=True)
    code = fields.Char(string="Código")
    active = fields.Boolean(default=True)
