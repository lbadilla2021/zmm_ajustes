from odoo import api, fields, models
from odoo.exceptions import ValidationError


class BarcaMaintenanceActivity(models.Model):
    _name = "barca.maintenance.activity"
    _description = "Actividad de mantención"
    _order = "category_id, technical_location_id, name"

    _sql_constraints = [
        (
            "unique_activity_per_location_category",
            "unique(name, category_id, technical_location_id)",
            "Ya existe una actividad con ese nombre para esta categoría y ubicación técnica.",
        )
    ]

    name = fields.Char(string="Nombre actividad", required=True)
    code = fields.Char(string="Código")
    active = fields.Boolean(default=True)

    category_id = fields.Many2one(
        "fleet.vehicle.model.category",
        string="Categoría de vehículo",
        required=True,
        index=True,
    )

    technical_location_id = fields.Many2one(
        "barca.technical.location",
        string="Ubicación técnica",
        required=True,
        index=True,
        domain="[('category_id', '=', category_id)]",
    )

    # Campo relacionado para exponer el código de la ubicación técnica en vistas
    # y exportaciones sin necesidad de navegar la relación manualmente.
    technical_location_code = fields.Char(
        string="Código ubic. técnica",
        related="technical_location_id.code",
        store=True,
        readonly=True,
    )


    estimated_duration = fields.Float(
        string="Duración estimada (hrs)",
        digits=(6, 2),
    )

    note = fields.Text(string="Instrucciones técnicas")

    @api.constrains("category_id", "technical_location_id")
    def _check_location_category(self):
        for rec in self:
            if (
                rec.technical_location_id
                and rec.technical_location_id.category_id
                and rec.technical_location_id.category_id != rec.category_id
            ):
                raise ValidationError(
                    "La categoría de la ubicación técnica debe coincidir "
                    "con la categoría de la actividad."
                )
