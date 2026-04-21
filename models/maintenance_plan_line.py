from odoo import api, fields, models
from odoo.exceptions import ValidationError


class BarcaMaintenancePlanLine(models.Model):
    _name = "barca.maintenance.plan.line"
    _description = "Línea de actividad del plan de mantención"
    _order = "sequence, id"

    sequence = fields.Integer(string="Secuencia", default=10)

    plan_id = fields.Many2one(
        "barca.maintenance.plan",
        string="Plan",
        required=True,
        ondelete="cascade",
        index=True,
    )

    # Heredado del plan para poder usarlo en domain de los campos de la línea
    category_id = fields.Many2one(
        "fleet.vehicle.model.category",
        related="plan_id.category_id",
        store=True,
        string="Categoría",
    )

    technical_location_id = fields.Many2one(
        "barca.technical.location",
        string="Ubicación técnica",
        required=True,
        index=True,
        domain="[('category_id', '=?', category_id)]",
    )

    intervention_type_id = fields.Many2one(
        "barca.intervention.type",
        string="Tipo de intervención",
        required=True,
    )

    activity_id = fields.Many2one(
        "barca.maintenance.activity",
        string="Actividad",
        required=True,
        domain="[('category_id', '=?', category_id), "
               "('technical_location_id', '=?', technical_location_id)]",
    )

    estimated_duration = fields.Float(
        string="Duración estimada (hrs)",
        digits=(6, 2),
    )

    note = fields.Text(string="Observaciones")

    @api.onchange("technical_location_id")
    def _onchange_technical_location_id(self):
        """Al cambiar la ubicación técnica, limpiar la actividad si ya no es
        compatible y proponer el dominio correcto."""
        if self.activity_id and (
            self.activity_id.technical_location_id != self.technical_location_id
        ):
            self.activity_id = False
        return {
            "domain": {
                "activity_id": [
                    ("category_id", "=?", self.category_id.id or False),
                    ("technical_location_id", "=?", self.technical_location_id.id or False),
                ]
            }
        }

    @api.onchange("activity_id")
    def _onchange_activity_id(self):
        """Al seleccionar actividad, autocompletar tipo de intervención siempre
        (valor por defecto modificable) y duración estimada si la línea no tiene
        valor propio aún."""
        if self.activity_id:
            # Tipo de intervención: se carga siempre desde el maestro como valor
            # por defecto. El usuario puede modificarlo libremente después.
            if self.activity_id.intervention_type_id:
                self.intervention_type_id = self.activity_id.intervention_type_id
            # Duración: se sugiere solo si la línea no tiene valor aún
            if self.activity_id.estimated_duration and not self.estimated_duration:
                self.estimated_duration = self.activity_id.estimated_duration

    @api.constrains("activity_id", "technical_location_id")
    def _check_activity_location_consistency(self):
        for rec in self:
            if (
                rec.activity_id
                and rec.technical_location_id
                and rec.activity_id.technical_location_id != rec.technical_location_id
            ):
                raise ValidationError(
                    "La actividad '%s' no corresponde a la ubicación técnica '%s'."
                    % (rec.activity_id.name, rec.technical_location_id.name)
                )

    @api.constrains("activity_id", "category_id")
    def _check_activity_category_consistency(self):
        for rec in self:
            if (
                rec.activity_id
                and rec.category_id
                and rec.activity_id.category_id != rec.category_id
            ):
                raise ValidationError(
                    "La actividad '%s' no corresponde a la categoría '%s'."
                    % (rec.activity_id.name, rec.category_id.name)
                )
