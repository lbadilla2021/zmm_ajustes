from odoo import api, fields, models
from odoo.exceptions import ValidationError


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
    technical_location_id = fields.Many2one(
        "barca.technical.location",
        string="Ubicación técnica",
        tracking=True,
    )

    intervention_type_id = fields.Many2one(
        "barca.intervention.type",
        string="Tipo de intervención",
        tracking=True,
    )

    priority = fields.Selection(
        [
            ("low", "Baja"),
            ("medium", "Media"),
            ("high", "Alta"),
            ("critical", "Crítica"),
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
                    "El equipo de mantenimiento debe corresponder al mismo vehículo del aviso."
                )

    @api.constrains("vehicle_id", "technical_location_id")
    def _check_technical_location_category(self):
        for record in self:
            if (
                record.technical_location_id
                and record.vehicle_id
                and record.technical_location_id.category_id
                and record.vehicle_id.category_id
                and record.technical_location_id.category_id
                != record.vehicle_id.category_id
            ):
                raise ValidationError(
                    "La ubicación técnica debe ser compatible con la categoría del vehículo."
                )

    @api.constrains("state")
    def _check_state_allowed(self):
        allowed_states = {
            key
            for key, _label in self._fields["state"].selection
        }
        for record in self:
            if record.state not in allowed_states:
                raise ValidationError("El estado del aviso no es válido.")

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
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "barca.maintenance.alert"
                ) or "Nuevo"

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
