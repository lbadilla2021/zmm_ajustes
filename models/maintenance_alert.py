from odoo import api, fields, models


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
