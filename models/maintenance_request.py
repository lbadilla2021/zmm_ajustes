from odoo import api, fields, models
from odoo.exceptions import ValidationError


class MaintenanceRequest(models.Model):
    _inherit = "maintenance.request"

    # La OT gestiona su propio ciclo de programación, ejecución, revisión y cierre.
    # El aviso asociado permanece en "Con OT creada" hasta que el usuario lo cierre
    # explícitamente, una vez que la OT esté en una etapa terminada.

    barca_alert_id = fields.Many2one(
        "barca.maintenance.alert",
        string="Aviso Barca",
        index=True,
    )
    barca_activity_line_ids = fields.One2many(
        "barca.maintenance.workorder.line",
        "maintenance_request_id",
        string="Actividades",
    )
    barca_activity_count = fields.Integer(
        string="N° actividades Barca",
        compute="_compute_barca_activity_count",
    )

    @api.depends("barca_activity_line_ids")
    def _compute_barca_activity_count(self):
        for request in self:
            request.barca_activity_count = len(request.barca_activity_line_ids)


class BarcaMaintenanceWorkorderLine(models.Model):
    _name = "barca.maintenance.workorder.line"
    _description = "Actividad de orden de trabajo Barca"
    _order = "sequence, id"

    sequence = fields.Integer(string="Secuencia", default=10)

    maintenance_request_id = fields.Many2one(
        "maintenance.request",
        string="Orden de Trabajo",
        required=True,
        ondelete="cascade",
        index=True,
    )

    alert_line_id = fields.Many2one(
        "barca.maintenance.alert.line",
        string="Actividad del aviso origen",
        ondelete="set null",
    )

    alert_id = fields.Many2one(
        "barca.maintenance.alert",
        string="Aviso",
        related="alert_line_id.alert_id",
        store=True,
        readonly=True,
    )

    plan_line_id = fields.Many2one(
        "barca.maintenance.plan.line",
        string="Línea de plan origen",
        related="alert_line_id.plan_line_id",
        store=True,
        readonly=True,
    )

    technical_location_id = fields.Many2one(
        "barca.technical.location",
        string="Ubicación técnica",
        required=True,
    )

    intervention_type_id = fields.Many2one(
        "barca.intervention.type",
        string="Tipo de intervención",
    )

    activity_id = fields.Many2one(
        "barca.maintenance.activity",
        string="Actividad",
        required=True,
    )

    description = fields.Text(string="Descripción")

    estimated_duration = fields.Float(
        string="Duración estimada (hrs)",
        digits=(6, 2),
    )

    state = fields.Selection(
        [
            ("pending", "Pendiente"),
            ("in_progress", "En proceso"),
            ("notified", "Notificada"),
            ("closed", "Cerrada"),
        ],
        string="Estado operativo",
        default="pending",
        required=True,
    )

    note = fields.Text(string="Observaciones")

    material_line_ids = fields.One2many(
        "barca.maintenance.workorder.line.material",
        "workorder_line_id",
        string="Materiales / Repuestos / Kits",
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
        "maintenance_request_id.name",
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

            label = " - ".join(parts) or "Actividad OT"
            if rec.sequence:
                label = "[%s] %s" % (rec.sequence, label)
            if rec.maintenance_request_id:
                label = "%s / %s" % (rec.maintenance_request_id.display_name, label)

            rec.display_name = label

    @api.depends("material_line_ids")
    def _compute_material_count(self):
        for rec in self:
            rec.material_count = len(rec.material_line_ids)

    @api.depends(
        "material_line_ids.sequence",
        "material_line_ids.product_id",
        "material_line_ids.product_id.display_name",
        "material_line_ids.estimated_quantity",
        "material_line_ids.product_uom_id",
    )
    def _compute_material_summary(self):
        for rec in self:
            lines = rec.material_line_ids.sorted(lambda line: line.sequence)
            parts = []

            for line in lines[:3]:
                if not line.product_id:
                    continue

                qty = line.estimated_quantity or 0.0
                qty_text = ("%s" % qty).rstrip("0").rstrip(".")
                uom = line.product_uom_id.name or line.product_id.uom_id.name or ""
                parts.append(
                    "%s x%s %s" % (line.product_id.display_name, qty_text, uom)
                )

            if not parts:
                rec.material_summary = False
                continue

            remaining = len(lines) - len(parts)
            summary = ", ".join(parts)
            if remaining > 0:
                summary = "%s (+%s)" % (summary, remaining)

            rec.material_summary = summary


class BarcaMaintenanceWorkorderLineMaterial(models.Model):
    _name = "barca.maintenance.workorder.line.material"
    _description = "Material, repuesto o kit por actividad de OT Barca"
    _order = "sequence, id"

    sequence = fields.Integer(string="Secuencia", default=10)

    workorder_line_id = fields.Many2one(
        "barca.maintenance.workorder.line",
        string="Actividad de OT",
        required=True,
        ondelete="cascade",
        index=True,
    )

    maintenance_request_id = fields.Many2one(
        "maintenance.request",
        string="Orden de Trabajo",
        related="workorder_line_id.maintenance_request_id",
        store=True,
        readonly=True,
    )

    alert_line_material_id = fields.Many2one(
        "barca.maintenance.alert.line.material",
        string="Material del aviso origen",
        ondelete="set null",
    )

    product_id = fields.Many2one(
        "product.product",
        string="Repuesto / Kit / Material",
        required=True,
    )

    product_uom_id = fields.Many2one(
        "uom.uom",
        string="UdM",
        required=True,
    )

    product_uom_category_id = fields.Many2one(
        "uom.category",
        related="product_id.uom_id.category_id",
        readonly=True,
    )

    estimated_quantity = fields.Float(
        string="Cantidad estimada",
        required=True,
        default=1.0,
    )

    reserved_quantity = fields.Float(string="Cantidad reservada", default=0.0)
    withdrawn_quantity = fields.Float(string="Cantidad retirada", default=0.0)
    consumed_quantity = fields.Float(string="Cantidad consumida", default=0.0)
    returned_quantity = fields.Float(string="Cantidad devuelta", default=0.0)

    note = fields.Text(string="Observación")

    @api.depends(
        "sequence",
        "workorder_line_id.display_name",
        "product_id.display_name",
        "estimated_quantity",
        "product_uom_id.display_name",
    )
    def _compute_display_name(self):
        for rec in self:
            product = rec.product_id.display_name or "Material OT"
            qty = rec.estimated_quantity or 0.0
            qty_text = ("%s" % qty).rstrip("0").rstrip(".")
            uom = rec.product_uom_id.display_name or ""
            label = "%s x%s %s" % (product, qty_text, uom)
            if rec.workorder_line_id:
                label = "%s / %s" % (rec.workorder_line_id.display_name, label)

            rec.display_name = label

    @api.onchange("product_id")
    def _onchange_product_id(self):
        for rec in self:
            rec.product_uom_id = rec.product_id.uom_id if rec.product_id else False

    @api.constrains(
        "estimated_quantity",
        "reserved_quantity",
        "withdrawn_quantity",
        "consumed_quantity",
        "returned_quantity",
    )
    def _check_quantities_non_negative(self):
        quantity_fields = (
            "estimated_quantity",
            "reserved_quantity",
            "withdrawn_quantity",
            "consumed_quantity",
            "returned_quantity",
        )
        labels = dict(self._fields_get_quantity_labels(quantity_fields))
        for rec in self:
            for field_name in quantity_fields:
                if rec[field_name] < 0:
                    raise ValidationError(
                        "La cantidad '%s' debe ser mayor o igual a cero."
                        % labels[field_name]
                    )

    def _fields_get_quantity_labels(self, quantity_fields):
        for field_name in quantity_fields:
            yield field_name, self._fields[field_name].string

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
