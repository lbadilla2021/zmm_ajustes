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

    material_template_line_ids = fields.One2many(
        "barca.maintenance.activity.material",
        "activity_id",
        string="Materiales / Repuestos / Kits estándar",
    )

    material_count = fields.Integer(
        string="N° materiales",
        compute="_compute_material_count",
    )

    material_summary = fields.Char(
        string="Materiales estándar",
        compute="_compute_material_summary",
    )

    @api.depends("material_template_line_ids")
    def _compute_material_count(self):
        for rec in self:
            rec.material_count = len(rec.material_template_line_ids)

    @api.depends(
        "material_template_line_ids.sequence",
        "material_template_line_ids.product_id",
        "material_template_line_ids.product_id.display_name",
        "material_template_line_ids.quantity",
        "material_template_line_ids.product_uom_id",
    )
    def _compute_material_summary(self):
        for rec in self:
            lines = rec.material_template_line_ids.sorted(lambda line: line.sequence)
            parts = []

            for line in lines[:3]:
                if not line.product_id:
                    continue

                qty = line.quantity or 0.0
                uom = line.product_uom_id.name or line.product_id.uom_id.name or ""
                parts.append("%s x %s %s" % (line.product_id.display_name, qty, uom))

            if not parts:
                rec.material_summary = False
                continue

            remaining = len(lines) - len(parts)
            summary = ", ".join(parts)
            if remaining > 0:
                summary = "%s (+%s)" % (summary, remaining)

            rec.material_summary = summary

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


class BarcaMaintenanceActivityMaterial(models.Model):
    _name = "barca.maintenance.activity.material"
    _description = "Material, repuesto o kit estándar por actividad"
    _order = "sequence, id"

    sequence = fields.Integer(string="Secuencia", default=10)

    activity_id = fields.Many2one(
        "barca.maintenance.activity",
        string="Actividad",
        required=True,
        ondelete="cascade",
        index=True,
    )

    product_id = fields.Many2one(
        "product.product",
        string="Repuesto / Kit / Material",
        required=True,
        index=True,
    )

    product_uom_id = fields.Many2one(
        "uom.uom",
        string="UdM",
        required=True,
    )

    product_uom_category_id = fields.Many2one(
        "uom.category",
        string="Categoría UdM",
        related="product_id.uom_id.category_id",
        readonly=True,
    )

    quantity = fields.Float(
        string="Cantidad estándar",
        required=True,
        default=1.0,
    )

    note = fields.Text(string="Observación")

    @api.onchange("product_id")
    def _onchange_product_id(self):
        for rec in self:
            rec.product_uom_id = rec.product_id.uom_id if rec.product_id else False

    @api.constrains("quantity")
    def _check_quantity_positive(self):
        for rec in self:
            if rec.quantity <= 0:
                raise ValidationError("La cantidad estándar debe ser mayor que cero.")

    @api.constrains("product_id", "product_uom_id")
    def _check_product_and_uom(self):
        for rec in self:
            if not rec.product_id:
                raise ValidationError("Debe definir un Repuesto / Kit / Material.")

            if not rec.product_uom_id:
                raise ValidationError("Debe definir una unidad de medida.")

            if rec.product_uom_id.category_id != rec.product_id.uom_id.category_id:
                raise ValidationError(
                    "La unidad de medida debe pertenecer a la misma categoría "
                    "que la unidad del producto."
                )