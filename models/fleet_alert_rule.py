import re

from odoo import fields, models


class BarcaFleetAlertRule(models.Model):
    _name = "barca.fleet.alert.rule"
    _description = "Alerta de Flotilla"
    _rec_name = "rule"
    _order = "rule"

    rule = fields.Char(string="Regla", required=True)
    email_names = fields.Text(
        string="Nombres de correo",
        help=(
            "Lista de correos de distribución para la regla. "
            "Puede ingresar más de uno separado por coma, punto y coma, espacio "
            "o salto de línea."
        ),
    )

    _sql_constraints = [
        (
            "rule_unique",
            "unique(rule)",
            "Ya existe una lista de distribución para esa regla.",
        ),
    ]

    def _get_recipients_for_rule(self, rule):
        alert_rule = self.sudo().search([("rule", "=", rule)], limit=1)
        if not alert_rule.email_names:
            return []
        return [
            email.strip()
            for email in re.split(r"[,;\s]+", alert_rule.email_names)
            if email.strip()
        ]
