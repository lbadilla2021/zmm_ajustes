from odoo import api, fields, models


class BarcaTechnicalLocation(models.Model):
    _name = "barca.technical.location"
    _description = "Ubicación técnica"
    _order = "category_id, parent_id, name"

    name = fields.Char(string="Nombre", required=True)
    code = fields.Char(string="Código", required=True)

    category_id = fields.Many2one(
        "fleet.vehicle.model.category",
        string="Categoría de vehículo",
        required=True,
    )

    parent_id = fields.Many2one(
        "barca.technical.location",
        string="Ubicación padre",
        ondelete="cascade",
    )

    child_ids = fields.One2many(
        "barca.technical.location",
        "parent_id",
        string="Sububicaciones",
    )

    complete_name = fields.Char(
        string="Ruta completa",
        compute="_compute_complete_name",
        store=True,
    )

    level = fields.Integer(string="Nivel")

    kit_id = fields.Many2one(
        "barca.maintenance.kit",
        string="Kit sugerido",
    )

    estimated_useful_life = fields.Float(string="Vida útil estimada")

    reference_supplier_id = fields.Many2one(
        "res.partner",
        string="Proveedor referencia",
    )

    note = fields.Text(string="Notas técnicas")

    _sql_constraints = [
        (
            "unique_location_per_parent_category",
            "unique(name, category_id, parent_id)",
            "Ya existe una ubicación técnica con ese nombre en este nivel y categoría.",
        )
    ]

    @api.depends("name", "parent_id.complete_name")
    def _compute_complete_name(self):
        for rec in self:
            parts = []
            current = rec
            while current:
                parts.append(current.name)
                current = current.parent_id
            rec.complete_name = " / ".join(reversed(parts))
