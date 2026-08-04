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
        readonly=True,
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
        tracking=True,
    )
    equipment_id = fields.Many2one(
        "maintenance.equipment",
        string="Equipo de mantenimiento",
        required=True,
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
    detailed_location = fields.Text(
        string="Planta y Lugar detallado",
        tracking=True,
    )
    vehicle_status = fields.Selection(
        [
            ("operativo", "Operativo"),
            ("no_operativo", "No operativo"),
        ],
        string="Estado del vehículo",
        default="operativo",
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
    offline_local_uuid = fields.Char(
        string="UUID offline",
        copy=False,
        index=True,
        help="UUID generado por el cliente cuando la solicitud fue creada sin conexion. "
             "Permite idempotencia al re-sincronizar el mismo formulario.",
    )
    external_token_user_id = fields.Many2one(
        "zweb.offline.form.token.user",
        string="Usuario externo",
        copy=False,
        readonly=True,
        index=True,
        tracking=True,
    )
    external_login_snapshot = fields.Char(
        string="Login externo",
        copy=False,
        readonly=True,
        tracking=True,
    )
    offline_auth_method = fields.Selection(
        [
            ("odoo_user", "Usuario Odoo"),
            ("external_token", "Token externo"),
        ],
        string="Metodo de autenticacion",
        copy=False,
        readonly=True,
        default="odoo_user",
        tracking=True,
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

    @api.onchange("equipment_id")
    def _onchange_equipment_id_set_vehicle(self):
        for record in self:
            record.vehicle_id = record.equipment_id.vehicle_id

    def _barca_is_restricted_conductor(self):
        return (
            not self.env.su
            and self.env.user.has_group("zmm_ajustes.group_barca_conductor")
        )

    @api.model_create_multi
    def create(self, vals_list):
        restricted_conductor = self._barca_is_restricted_conductor()
        for vals in vals_list:
            if restricted_conductor:
                vals["requested_by_id"] = self.env.user.id
            vals["request_date"] = fields.Datetime.now()
            if vals.get("name", "Nuevo") == "Nuevo":
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code("barca.maintenance.request")
                    or "Nuevo"
                )

            equipment_id = vals.get("equipment_id")
            if equipment_id:
                equipment = self.env["maintenance.equipment"].browse(equipment_id)
                vals["vehicle_id"] = equipment.vehicle_id.id or False

        return super().create(vals_list)

    def _get_equipment_for_vehicle(self, vehicle_id):
        if not vehicle_id:
            return False
        return self.env["maintenance.equipment"].search(
            [("vehicle_id", "=", vehicle_id)],
            limit=1,
        )

    def _prepare_origin_note(self):
        self.ensure_one()
        origin_lines = [
            "Solicitud de Mantención %s creada por %s."
            % (self.name, self.requested_by_id.name)
        ]
        if self.external_login_snapshot:
            origin_lines.append("Usuario externo: %s" % self.external_login_snapshot)
        if self.detailed_location:
            origin_lines.append("Planta y Lugar detallado: %s" % self.detailed_location)
        if self.vehicle_status:
            status_label = dict(self._fields["vehicle_status"].selection).get(
                self.vehicle_status,
                self.vehicle_status,
            )
            origin_lines.append("Estado del vehículo: %s" % status_label)
        return "\n".join(origin_lines)

    def write(self, vals):
        vals = dict(vals)
        vals.pop("request_date", None)

        if (
            self._barca_is_restricted_conductor()
            and "requested_by_id" in vals
            and vals["requested_by_id"] != self.env.user.id
        ):
            raise ValidationError(
                "El conductor no puede cambiar el solicitante de una solicitud."
            )

        if "equipment_id" in vals:
            equipment = self.env["maintenance.equipment"].browse(vals["equipment_id"])
            vals["vehicle_id"] = equipment.vehicle_id.id or False
        return super().write(vals)

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
            if not request.vehicle_id:
                raise ValidationError(
                    "El equipo de mantenimiento seleccionado no tiene un "
                    "vehículo asociado."
                )

            alert_vals = {
                "source_type": "request",
                "source_reference": request.name,
                "source_request_id": request.id,
                "vehicle_id": request.vehicle_id.id,
                "equipment_id": request.equipment_id.id,
                "priority": request.priority,
                "description": request.description,
                "origin_note": request._prepare_origin_note(),
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
