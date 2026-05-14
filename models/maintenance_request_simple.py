from odoo import api, fields, models
from odoo.exceptions import ValidationError


class BarcaMaintenanceRequest(models.Model):
    _name = "barca.maintenance.request"
    _description = "Solicitud de Mantención"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "request_date desc, id desc"

    name = fields.Char(
        string="N° Solicitud",
        required=True,
        copy=False,
        readonly=True,
        default="Nuevo",
        tracking=True,
    )
    request_date = fields.Datetime(
        string="Fecha de solicitud",
        default=fields.Datetime.now,
        required=True,
        tracking=True,
    )
    requested_by_id = fields.Many2one(
        "res.users",
        string="Solicitado por",
        default=lambda self: self.env.user,
        required=True,
        tracking=True,
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
    priority = fields.Selection(
        [
            ("low", "Baja"),
            ("medium", "Media"),
            ("high", "Alta"),
        ],
        string="Prioridad sugerida",
        default="medium",
        required=True,
        tracking=True,
    )
    description = fields.Text(
        string="Descripción de la necesidad",
        required=True,
        tracking=True,
    )
    state = fields.Selection(
        [
            ("draft", "Nueva"),
            ("alert_created", "Aviso creado"),
            ("cancelled", "Cancelada"),
        ],
        string="Estado",
        default="draft",
        required=True,
        tracking=True,
    )
    alert_id = fields.Many2one(
        "barca.maintenance.alert",
        string="Aviso generado",
        readonly=True,
        copy=False,
    )

    @api.constrains("vehicle_id", "equipment_id")
    def _check_vehicle_equipment_consistency(self):
        for record in self:
            if (
                record.vehicle_id
                and record.equipment_id
                and record.equipment_id.vehicle_id != record.vehicle_id
            ):
                raise ValidationError(
                    "El equipo de mantenimiento debe corresponder al vehículo "
                    "de la solicitud."
                )

    @api.onchange("vehicle_id")
    def _onchange_vehicle_id_set_equipment(self):
        for record in self:
            if record.vehicle_id:
                record.equipment_id = self.env["maintenance.equipment"].search(
                    [("vehicle_id", "=", record.vehicle_id.id)],
                    limit=1,
                )
            else:
                record.equipment_id = False

    @api.model_create_multi
    def create(self, vals_list):
        equipment_by_vehicle = {}

        for vals in vals_list:
            if vals.get("name", "Nuevo") == "Nuevo":
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code("barca.maintenance.request")
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

    def action_cancel(self):
        for request in self:
            if request.alert_id:
                raise ValidationError(
                    "No se puede cancelar una solicitud que ya generó un aviso."
                )
            request.state = "cancelled"

    def action_create_alert(self):
        created_alerts = self.env["barca.maintenance.alert"]

        for request in self:
            if request.state == "cancelled":
                raise ValidationError(
                    "No se puede generar un aviso desde una solicitud cancelada."
                )
            if request.alert_id:
                raise ValidationError("La solicitud ya tiene un aviso generado.")

            alert_vals = {
                "source_type": "request",
                "source_reference": request.name,
                "source_request_id": request.id,
                "vehicle_id": request.vehicle_id.id,
                "equipment_id": request.equipment_id.id,
                "priority": request.priority,
                "description": request.description,
                "origin_note": "Solicitud de Mantención %s creada por %s."
                % (request.name, request.requested_by_id.name),
            }
            alert = self.env["barca.maintenance.alert"].create(alert_vals)
            request.write({"alert_id": alert.id, "state": "alert_created"})
            created_alerts |= alert

        if len(created_alerts) == 1:
            return self.action_view_alert()

        return {
            "type": "ir.actions.act_window",
            "name": "Avisos generados",
            "res_model": "barca.maintenance.alert",
            "view_mode": "list,form",
            "domain": [("id", "in", created_alerts.ids)],
            "target": "current",
        }

    def action_view_alert(self):
        self.ensure_one()
        if not self.alert_id:
            raise ValidationError("La solicitud no tiene un aviso generado.")
        return {
            "type": "ir.actions.act_window",
            "name": "Aviso generado",
            "res_model": "barca.maintenance.alert",
            "view_mode": "form",
            "views": [(False, "form")],
            "res_id": self.alert_id.id,
            "target": "current",
        }
