import logging

from odoo import api, fields, models
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
            ("pending_evaluation", "Pendiente evaluación"),
            ("approved", "Aprobado"),
            ("rejected", "Rechazado"),
            ("in_progress", "En proceso"),
            ("in_review", "En revisión"),
            ("closed", "Cerrado"),
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
    approved_by_id = fields.Many2one("res.users", string="Aprobado por")
    closed_by_id = fields.Many2one("res.users", string="Cerrado por")

    maintenance_request_id = fields.Many2one(
        "maintenance.request",
        string="OT asociada",
        readonly=True,
    )

    _allowed_state_transitions = {
        "pending_evaluation": {"approved", "rejected"},
        "approved": {"in_progress", "rejected"},
        "in_progress": {"in_review"},
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

    def action_approve(self):
        self._validate_state_transition("approved")
        self._write_state_transition(
            "approved",
            {
                "evaluated_by_id": self.env.user.id,
                "approved_by_id": self.env.user.id,
                "evaluation_date": fields.Datetime.now(),
            },
        )

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
        self._validate_state_transition("in_progress")
        self._write_state_transition("in_progress")

    def action_review(self):
        self._validate_state_transition("in_review")
        self._write_state_transition(
            "in_review",
            {"review_date": fields.Datetime.now()},
        )

    def action_close(self):
        self._validate_state_transition("closed")
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
                    "Solo se puede crear una OT para avisos en estado Aprobado."
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
            }
            if "category_id" in self.env["maintenance.request"]._fields:
                equipment_category = alert.equipment_id.category_id
                if equipment_category:
                    request_vals["category_id"] = equipment_category.id

            request = self.env["maintenance.request"].create(request_vals)
            alert.with_context(allow_alert_state_write=True).write(
                {"maintenance_request_id": request.id}
            )
            alert.action_start()

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
