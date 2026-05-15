import logging

from odoo import Command, api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class BarcaMaintenanceAlert(models.Model):
    _name = "barca.maintenance.alert"
    _description = "Aviso de Mantención"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc, id desc"

    name = fields.Char(
        string="N° Aviso",
        required=True,
        copy=False,
        readonly=True,
        default="Nuevo",
        tracking=True,
    )

    description = fields.Text(string="Descripción", tracking=True)
    origin_note = fields.Text(string="Observación de origen")

    source_type = fields.Selection(
        [
            ("pm", "PM"),
            ("checklist", "Checklist"),
            ("request", "Solicitud"),
        ],
        string="Origen",
        required=True,
        tracking=True,
    )
    source_reference = fields.Char(string="Referencia de origen")
    pm_id = fields.Many2one(
        "barca.maintenance.plan",
        string="Plan de mantenimiento",
        index=True,
    )
    source_request_id = fields.Many2one(
        "barca.maintenance.request",
        string="Solicitud de Mantención origen",
        index=True,
    )
    checklist_id = fields.Many2one(
        "barca.maintenance.checklist",
        string="Checklist origen",
        index=True,
    )

    vehicle_id = fields.Many2one(
        "fleet.vehicle",
        string="Vehículo",
        required=True,
        tracking=True,
    )
    equipment_id = fields.Many2one(
        "maintenance.equipment",
        string="Equipo de mantenimiento",
        tracking=True,
    )

    # Líneas de actividades propagadas desde el plan
    alert_line_ids = fields.One2many(
        "barca.maintenance.alert.line",
        "alert_id",
        string="Actividades",
    )

    priority = fields.Selection(
        [
            ("low", "Baja"),
            ("medium", "Media"),
            ("high", "Alta"),
        ],
        string="Prioridad",
        default="medium",
        tracking=True,
    )

    state = fields.Selection(
        [
            ("pending_evaluation", "Nuevo"),
            ("approved", "En evaluación"),
            ("in_progress", "Con OT creada"),
            ("rejected", "Rechazado"),
            ("closed", "Cerrado"),
            ("in_review", "En revisión (legado)"),
        ],
        string="Estado",
        default="pending_evaluation",
        required=True,
        tracking=True,
    )

    odometer = fields.Float(string="Odómetro")
    operating_hours = fields.Float(string="Horas de operación")

    alert_date = fields.Datetime(
        string="Fecha del aviso",
        default=fields.Datetime.now,
        required=True,
        tracking=True,
    )
    evaluation_date = fields.Datetime(string="Fecha de evaluación")
    review_date = fields.Datetime(string="Fecha de revisión")
    close_date = fields.Datetime(string="Fecha de cierre")

    evaluated_by_id = fields.Many2one("res.users", string="Evaluado por")
    approved_by_id = fields.Many2one(
        "res.users",
        string="Tomado para evaluación por",
    )
    closed_by_id = fields.Many2one("res.users", string="Cerrado por")

    maintenance_request_id = fields.Many2one(
        "maintenance.request",
        string="OT asociada",
        readonly=True,
    )

    _allowed_state_transitions = {
        "pending_evaluation": {"approved", "rejected"},
        "approved": {"in_progress", "rejected"},
        "in_progress": {"closed"},
        # Compatibilidad para avisos creados antes del ajuste de flujo.
        "in_review": {"closed"},
    }

    # -------------------------------------------------------------------------
    # Transiciones de estado
    # -------------------------------------------------------------------------

    def _validate_state_transition(self, new_state):
        for record in self:
            allowed_targets = self._allowed_state_transitions.get(record.state, set())
            if new_state not in allowed_targets:
                raise ValidationError(
                    "Transición de estado no permitida: %(current)s → %(new)s."
                    % {
                        "current": dict(self._fields["state"].selection).get(
                            record.state, record.state
                        ),
                        "new": dict(self._fields["state"].selection).get(
                            new_state, new_state
                        ),
                    }
                )

    def _write_state_transition(self, new_state, extra_vals=None):
        vals = dict(extra_vals or {})
        vals["state"] = new_state
        self.with_context(allow_alert_state_write=True).write(vals)

    def action_take_for_evaluation(self):
        self._validate_state_transition("approved")
        self._write_state_transition(
            "approved",
            {
                "evaluated_by_id": self.env.user.id,
                "approved_by_id": self.env.user.id,
                "evaluation_date": fields.Datetime.now(),
            },
        )

    def action_approve(self):
        return self.action_take_for_evaluation()

    def action_reject(self):
        self._validate_state_transition("rejected")
        self._write_state_transition(
            "rejected",
            {
                "evaluated_by_id": self.env.user.id,
                "evaluation_date": fields.Datetime.now(),
            },
        )

    def action_start(self):
        raise ValidationError(
            "La ejecución se gestiona en la OT asociada, no directamente en el aviso."
        )

    def action_review(self):
        raise ValidationError(
            "La revisión se gestiona en la OT asociada, no directamente en el aviso."
        )

    def action_close(self):
        self._validate_state_transition("closed")
        for alert in self:
            if not alert.maintenance_request_id:
                raise ValidationError(
                    "Solo se puede cerrar un aviso que tenga una OT asociada."
                )
            if not alert._is_maintenance_request_ready_to_close():
                raise ValidationError(
                    "Solo se puede cerrar el aviso cuando la OT esté en "
                    "Reparado o Desechar."
                )
        self._write_state_transition(
            "closed",
            {
                "closed_by_id": self.env.user.id,
                "close_date": fields.Datetime.now(),
            },
        )
        # Actualizar medidores del vehículo con los valores del aviso
        for alert in self:
            alert._update_vehicle_last_service()

    def _is_maintenance_request_ready_to_close(self):
        self.ensure_one()
        request = self.maintenance_request_id
        return bool(request and request.stage_id and request.stage_id.done)

    def action_view_maintenance_request(self):
        self.ensure_one()
        if not self.maintenance_request_id:
            raise ValidationError("El aviso no tiene una OT asociada.")
        return {
            "type": "ir.actions.act_window",
            "name": "OT asociada",
            "res_model": "maintenance.request",
            "view_mode": "form",
            "views": [(False, "form")],
            "res_id": self.maintenance_request_id.id,
            "target": "current",
        }

    def _update_vehicle_last_service(self):
        """
        Al cerrar un aviso PM, actualiza en el vehículo:
          - x_odometer_last_service  (km registrado en el aviso)
          - x_last_exit_date         (fecha de cierre)
          - x_operating_hours        (horas registradas en el aviso)

        Nunca retrocede un valor: solo actualiza si el nuevo valor
        es mayor o igual al que ya tenía el vehículo.
        """
        self.ensure_one()
        if not self.vehicle_id or self.source_type != "pm":
            return

        vehicle = self.vehicle_id
        update_vals = {}

        if (
            "x_odometer_last_service" in vehicle._fields
            and self.odometer
            and self.odometer > (vehicle.x_odometer_last_service or 0.0)
        ):
            update_vals["x_odometer_last_service"] = self.odometer

        if "x_last_exit_date" in vehicle._fields:
            close_date = fields.Date.today()
            if not vehicle.x_last_exit_date or close_date >= vehicle.x_last_exit_date:
                update_vals["x_last_exit_date"] = close_date

        if (
            "x_hours_last_service" in vehicle._fields
            and self.operating_hours
            and self.operating_hours > (vehicle.x_hours_last_service or 0.0)
        ):
            update_vals["x_hours_last_service"] = self.operating_hours

        if update_vals:
            vehicle.write(update_vals)

    def action_create_maintenance_request(self):
        for alert in self:
            if alert.state != "approved":
                raise ValidationError(
                    "Solo se puede crear una OT para avisos en estado En evaluación."
                )
            if alert.maintenance_request_id:
                raise ValidationError("El aviso ya tiene una OT asociada.")
            if not alert.equipment_id:
                raise ValidationError(
                    "Debe existir un equipo de mantenimiento para crear la OT."
                )

            # Construir descripción enriquecida con las actividades del aviso
            activities_summary = ""
            if alert.alert_line_ids:
                lines = []
                for line in alert.alert_line_ids:
                    lines.append(
                        "- [%s] %s — %s"
                        % (
                            line.technical_location_id.name or "",
                            line.activity_id.name or "",
                            line.intervention_type_id.name or "",
                        )
                    )
                activities_summary = "\n\nActividades:\n" + "\n".join(lines)

            request_vals = {
                "name": alert.name,
                "request_date": fields.Datetime.now(),
                "maintenance_type": "corrective",
                "description": (alert.description or "") + activities_summary,
                "equipment_id": alert.equipment_id.id,
                "barca_alert_id": alert.id,
                "barca_activity_line_ids": alert._prepare_workorder_activity_commands(),
            }
            if "category_id" in self.env["maintenance.request"]._fields:
                equipment_category = alert.equipment_id.category_id
                if equipment_category:
                    request_vals["category_id"] = equipment_category.id

            request = self.env["maintenance.request"].create(request_vals)
            alert._write_state_transition(
                "in_progress",
                {"maintenance_request_id": request.id},
            )

    def _prepare_workorder_activity_commands(self):
        self.ensure_one()

        commands = []
        for line in self.alert_line_ids.sorted(lambda alert_line: alert_line.sequence):
            commands.append(
                Command.create(
                    {
                        "sequence": line.sequence,
                        "alert_line_id": line.id,
                        "technical_location_id": line.technical_location_id.id,
                        "intervention_type_id": line.intervention_type_id.id,
                        "activity_id": line.activity_id.id,
                        "description": line.activity_id.note,
                        "estimated_duration": line.estimated_duration,
                        "state": "pending",
                        "note": line.note,
                        "material_line_ids": (
                            line._prepare_material_commands_from_alert_line()
                        ),
                    }
                )
            )

        return commands

    # -------------------------------------------------------------------------
    # Constrains y onchange
    # -------------------------------------------------------------------------

    @api.constrains("vehicle_id")
    def _check_vehicle_required(self):
        for record in self:
            if not record.vehicle_id:
                raise ValidationError("El vehículo es obligatorio para el aviso.")

    @api.constrains("vehicle_id", "equipment_id")
    def _check_vehicle_equipment_consistency(self):
        for record in self:
            if (
                record.equipment_id
                and record.vehicle_id
                and record.equipment_id.vehicle_id != record.vehicle_id
            ):
                raise ValidationError(
                    "El equipo de mantenimiento debe corresponder al mismo "
                    "vehículo del aviso."
                )

    @api.onchange("vehicle_id")
    def _onchange_vehicle_id_set_equipment(self):
        for record in self:
            if record.vehicle_id and not record.equipment_id:
                record.equipment_id = self.env["maintenance.equipment"].search(
                    [("vehicle_id", "=", record.vehicle_id.id)], limit=1
                )

    @api.model_create_multi
    def create(self, vals_list):
        equipment_by_vehicle = {}

        for vals in vals_list:
            if vals.get("name", "Nuevo") == "Nuevo":
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code("barca.maintenance.alert")
                    or "Nuevo"
                )

            vehicle_id = vals.get("vehicle_id")
            if vehicle_id and not vals.get("equipment_id"):
                if vehicle_id not in equipment_by_vehicle:
                    equipment = self.env["maintenance.equipment"].search(
                        [("vehicle_id", "=", vehicle_id)],
                        limit=1,
                    )
                    equipment_by_vehicle[vehicle_id] = equipment.id
                if equipment_by_vehicle[vehicle_id]:
                    vals["equipment_id"] = equipment_by_vehicle[vehicle_id]

        return super().create(vals_list)

    def write(self, vals):
        if "state" in vals and not self.env.context.get("allow_alert_state_write"):
            raise ValidationError(
                "No está permitido cambiar el estado manualmente. "
                "Use las acciones del aviso."
            )
        return super().write(vals)


class BarcaMaintenanceAlertLine(models.Model):
    _name = "barca.maintenance.alert.line"
    _description = "Línea de actividad del aviso de mantención"
    _order = "sequence, id"

    sequence = fields.Integer(string="Secuencia", default=10)

    alert_id = fields.Many2one(
        "barca.maintenance.alert",
        string="Aviso",
        required=True,
        ondelete="cascade",
        index=True,
    )

    # Referencia trazable al origen en el plan
    plan_line_id = fields.Many2one(
        "barca.maintenance.plan.line",
        string="Línea de plan origen",
        ondelete="set null",
    )

    technical_location_id = fields.Many2one(
        "barca.technical.location",
        string="Ubicación técnica",
        required=True,
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
    )

    estimated_duration = fields.Float(
        string="Duración estimada (hrs)",
        digits=(6, 2),
    )

    done = fields.Boolean(
        string="Realizada",
        default=False,
        tracking=True,
    )

    note = fields.Text(string="Observaciones")

    material_line_ids = fields.One2many(
        "barca.maintenance.alert.line.material",
        "alert_line_id",
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
        "alert_id.name",
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

            label = " - ".join(parts) or "Actividad del aviso"
            if rec.sequence:
                label = "[%s] %s" % (rec.sequence, label)
            if rec.alert_id:
                label = "%s / %s" % (rec.alert_id.display_name, label)

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

    @api.model
    def _prepare_material_commands_from_plan_line(self, plan_line):
        commands = []
        for material in plan_line.material_line_ids.sorted(
            lambda line: line.sequence
        ):
            commands.append(
                Command.create(
                    {
                        "sequence": material.sequence,
                        "plan_line_material_id": material.id,
                        "product_id": material.product_id.id,
                        "product_uom_id": material.product_uom_id.id,
                        "estimated_quantity": material.quantity,
                        "note": material.note,
                    }
                )
            )

        return commands

    def _prepare_material_commands_from_alert_line(self):
        self.ensure_one()

        commands = []
        for material in self.material_line_ids.sorted(
            lambda material_line: material_line.sequence
        ):
            commands.append(
                Command.create(
                    {
                        "sequence": material.sequence,
                        "alert_line_material_id": material.id,
                        "product_id": material.product_id.id,
                        "product_uom_id": material.product_uom_id.id,
                        "estimated_quantity": material.estimated_quantity,
                        "note": material.note,
                    }
                )
            )

        return commands

    def _prepare_workorder_material_commands(self):
        return self._prepare_material_commands_from_alert_line()


class BarcaMaintenanceAlertLineMaterial(models.Model):
    _name = "barca.maintenance.alert.line.material"
    _description = "Material, repuesto o kit por actividad del aviso"
    _order = "sequence, id"

    sequence = fields.Integer(string="Secuencia", default=10)

    alert_line_id = fields.Many2one(
        "barca.maintenance.alert.line",
        string="Actividad del aviso",
        required=True,
        ondelete="cascade",
        index=True,
    )

    alert_id = fields.Many2one(
        "barca.maintenance.alert",
        string="Aviso",
        related="alert_line_id.alert_id",
        store=True,
        readonly=True,
        index=True,
    )

    plan_line_material_id = fields.Many2one(
        "barca.maintenance.plan.line.material",
        string="Material de línea de plan origen",
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

    available_quantity = fields.Float(
        string="Disponible",
        compute="_compute_available_quantity",
        readonly=True,
    )

    note = fields.Text(string="Observación")

    @api.depends(
        "sequence",
        "alert_line_id.display_name",
        "product_id.display_name",
        "estimated_quantity",
        "product_uom_id.display_name",
    )
    def _compute_display_name(self):
        for rec in self:
            product = rec.product_id.display_name or "Material del aviso"
            qty = rec.estimated_quantity or 0.0
            qty_text = ("%s" % qty).rstrip("0").rstrip(".")
            uom = rec.product_uom_id.display_name or ""
            label = "%s x%s %s" % (product, qty_text, uom)
            if rec.alert_line_id:
                label = "%s / %s" % (rec.alert_line_id.display_name, label)

            rec.display_name = label

    @api.depends("product_id", "product_id.qty_available")
    def _compute_available_quantity(self):
        for rec in self:
            rec.available_quantity = (
                rec.product_id.qty_available if rec.product_id else 0.0
            )

    @api.onchange("product_id")
    def _onchange_product_id(self):
        for rec in self:
            rec.product_uom_id = rec.product_id.uom_id if rec.product_id else False

    @api.constrains("estimated_quantity")
    def _check_estimated_quantity_positive(self):
        for rec in self:
            if rec.estimated_quantity <= 0:
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
