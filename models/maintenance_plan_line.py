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

    material_line_ids = fields.One2many(
        "barca.maintenance.plan.line.material",
        "plan_line_id",
        string="Materiales / Repuestos / Kits",
    )

    material_count = fields.Integer(
        string="N° materiales",
        compute="_compute_material_count",
        store=True,
    )

    material_summary = fields.Char(
        string="Materiales",
        compute="_compute_material_summary",
        store=True,
    )

    @api.depends("material_line_ids.product_id")
    def _compute_material_count(self):
        for rec in self:
            rec.material_count = len(rec.material_line_ids)

    @api.depends(
        "material_line_ids.sequence",
        "material_line_ids.product_id",
        "material_line_ids.product_id.name",
    )
    def _compute_material_summary(self):
        for rec in self:
            product_names = [
                line.product_id.display_name
                for line in rec.material_line_ids.sorted(lambda line: line.sequence)
                if line.product_id
            ]
            if not product_names:
                rec.material_summary = False
                continue

            summary_names = product_names[:3]
            summary = ", ".join(summary_names)
            remaining = len(product_names) - len(summary_names)
            if remaining > 0:
                summary = "%s (+%s)" % (summary, remaining)
            rec.material_summary = summary

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
        if self.activity_id and self.activity_id.estimated_duration \
                and not self.estimated_duration:
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


class BarcaMaintenancePlanLineMaterial(models.Model):
    _name = "barca.maintenance.plan.line.material"
    _description = "Material, repuesto o kit por actividad del plan"
    _order = "sequence, id"

    sequence = fields.Integer(string="Secuencia", default=10)

    plan_line_id = fields.Many2one(
        "barca.maintenance.plan.line",
        string="Actividad del plan",
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
    )

    quantity = fields.Float(
        string="Cantidad estimada",
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
                raise ValidationError("La cantidad estimada debe ser mayor que cero.")

    @api.constrains("product_id")
    def _check_product_id(self):
        for rec in self:
            if not rec.product_id:
                raise ValidationError("Debe definir un Repuesto / Kit / Material.")

    @api.constrains("product_uom_id")
    def _check_product_uom_id_exists(self):
        for rec in self:
            if rec.product_uom_id and not rec.product_uom_id.exists():
                raise ValidationError("La UdM seleccionada debe existir.")
