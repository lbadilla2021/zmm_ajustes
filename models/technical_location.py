from odoo import api, fields, models


class BarcaTechnicalLocation(models.Model):
    _name = "barca.technical.location"
    _description = "Ubicación técnica"
    _parent_name = "parent_id"
    _parent_store = True
    _order = "category_id, parent_id, name"

    name = fields.Char(string="Nombre", required=True)
    code = fields.Char(string="Código", required=True)

    category_id = fields.Many2one(
        "fleet.vehicle.model.category",
        string="Categoría de vehículo",
        required=True,
    )

    company_id = fields.Many2one(
        "res.company",
        string="Compañía",
        default=lambda self: self.env.company,
    )

    parent_id = fields.Many2one(
        "barca.technical.location",
        string="Ubicación padre",
        domain="[('category_id', '=', category_id), ('company_id', 'in', [company_id, False]), ('id', '!=', id)]",
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

    parent_path = fields.Char(index=True)

    level = fields.Integer(
        string="Nivel",
        compute="_compute_level",
        store=True,
    )

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
                parts.append(current.name or "")
                current = current.parent_id
            rec.complete_name = " / ".join(
                part for part in reversed(parts) if part
            )

    @api.depends("parent_id", "parent_id.level")
    def _compute_level(self):
        for rec in self:
            rec.level = rec.parent_id.level + 1 if rec.parent_id else 0

    def _ensure_external_ids(self):
        """Crea un XMLID estable por código para facilitar imports parent_id/id."""
        imd_model = self.env["ir.model.data"].sudo()
        for rec in self.filtered("code"):
            existing = imd_model.search(
                [
                    ("module", "=", "zmm_ajustes"),
                    ("name", "=", rec.code),
                    ("model", "=", self._name),
                ],
                limit=1,
            )
            if not existing:
                imd_model.create(
                    {
                        "module": "zmm_ajustes",
                        "name": rec.code,
                        "model": self._name,
                        "res_id": rec.id,
                        "noupdate": True,
                    }
                )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._ensure_external_ids()
        return records

    def write(self, vals):
        result = super().write(vals)
        if "code" in vals:
            self._ensure_external_ids()
        return result
