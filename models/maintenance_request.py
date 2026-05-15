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
