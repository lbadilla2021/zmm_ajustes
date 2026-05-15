from odoo import Command, api, fields, models
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
        string="Materiales / Repuestos / Kits del plan",
    )

    material_count = fields.Integer(
        string="N° materiales",
        compute="_compute_material_count",
    )

    material_summary = fields.Char(
        string="Materiales",
        compute="_compute_material_summary",
    )

    @api.depends(
        "sequence",
        "plan_id.name",
        "activity_id.display_name",
        "technical_location_id.display_name",
    )
    def _compute_display_name(self):
        for rec in self:
            parts = []
            if rec.activity_id:
                parts.append(rec.activity_id.display_name)
            if rec.technical_location_id:
                parts.append(rec.technical_location_id.display_name)

            label = " - ".join(parts) or "Actividad del plan"
            if rec.sequence:
                label = "[%s] %s" % (rec.sequence, label)
            if rec.plan_id:
                label = "%s / %s" % (rec.plan_id.display_name, label)

            rec.display_name = label

    @api.depends("material_line_ids")
    def _compute_material_count(self):
        for rec in self:
            rec.material_count = len(rec.material_line_ids)

    @api.depends(
        "material_line_ids.sequence",
        "material_line_ids.product_id",
        "material_line_ids.product_id.display_name",
        "material_line_ids.quantity",
        "material_line_ids.product_uom_id",
    )
    def _compute_material_summary(self):
        for rec in self:
            lines = rec.material_line_ids.sorted(lambda line: line.sequence)
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

    @api.onchange("technical_location_id")
    def _onchange_technical_location_id(self):
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
        for rec in self:
            if rec.activity_id and rec.activity_id.estimated_duration:
                rec.estimated_duration = rec.activity_id.estimated_duration

            if rec.activity_id and rec.activity_id.material_template_line_ids:
                return {
                    "warning": {
                        "title": "Materiales estándar disponibles",
                        "message": (
                            "La actividad seleccionada tiene materiales estándar. "
                            "Abra la línea de actividad y use el botón "
                            "'Cargar materiales estándar' para copiarlos al plan."
                        ),
                    }
                }

        return {}

    def _prepare_material_commands_from_activity(self):
        self.ensure_one()

        commands = []
        for material in self.activity_id.material_template_line_ids.sorted(
            lambda line: line.sequence
        ):
            commands.append(
                Command.create(
                    {
                        "sequence": material.sequence,
                        "product_id": material.product_id.id,
                        "product_uom_id": material.product_uom_id.id,
                        "quantity": material.quantity,
                        "note": material.note,
                    }
                )
            )

        return commands

    def action_load_activity_materials(self):
        for rec in self:
            if not rec.activity_id:
                raise ValidationError(
                    "Debe seleccionar una actividad antes de cargar materiales estándar."
                )

            if not rec.activity_id.material_template_line_ids:
                raise ValidationError(
                    "La actividad seleccionada no tiene materiales estándar definidos."
                )

            if rec.material_line_ids:
                raise ValidationError(
                    "Esta actividad del plan ya tiene materiales asociados. "
                    "Elimine o ajuste manualmente las líneas existentes antes de "
                    "cargar los materiales estándar."
                )

            rec.write(
                {
                    "material_line_ids": rec._prepare_material_commands_from_activity()
                }
            )

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Materiales cargados",
                "message": "Se copiaron los materiales estándar de la actividad al plan.",
                "type": "success",
                "sticky": False,
            },
        }

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

    plan_id = fields.Many2one(
        "barca.maintenance.plan",
        string="Plan",
        related="plan_line_id.plan_id",
        store=True,
        readonly=True,
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
        string="Cantidad estimada",
        required=True,
        default=1.0,
    )

    note = fields.Text(string="Observación")

    @api.depends(
        "sequence",
        "plan_line_id.display_name",
        "product_id.display_name",
        "quantity",
        "product_uom_id.display_name",
    )
    def _compute_display_name(self):
        for rec in self:
            product = rec.product_id.display_name or "Material del plan"
            qty = rec.quantity or 0.0
            qty_text = ("%s" % qty).rstrip("0").rstrip(".")
            uom = rec.product_uom_id.display_name or ""
            label = "%s x%s %s" % (product, qty_text, uom)
            if rec.plan_line_id:
                label = "%s / %s" % (rec.plan_line_id.display_name, label)

            rec.display_name = label

    @api.onchange("product_id")
    def _onchange_product_id(self):
        for rec in self:
            rec.product_uom_id = rec.product_id.uom_id if rec.product_id else False

    @api.constrains("quantity")
    def _check_quantity_positive(self):
        for rec in self:
            if rec.quantity <= 0:
                raise ValidationError("La cantidad estimada debe ser mayor que cero.")

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