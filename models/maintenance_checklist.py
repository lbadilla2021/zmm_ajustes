from odoo import api, fields, models
from odoo.exceptions import ValidationError


CHECKLIST_TYPE_SELECTION = [
    ("checklist_camion", "Checklist Camion"),
    ("checklist_camion_equipo_ap", "Checklist Camion y Equipo AP"),
    ("checklist_camion_equipo_av", "Checklist Camion y Equipo AV"),
    ("checklist_vehiculo", "Checklist Vehiculo"),
]


class BarcaMaintenanceChecklistItem(models.Model):
    _name = "barca.maintenance.checklist.item"
    _description = "Ítem de control de checklist"
    _order = "checklist_type, sequence, id"

    checklist_type = fields.Selection(
        CHECKLIST_TYPE_SELECTION,
        string="Tipo de vehículo",
        required=True,
        index=True,
    )
    control_type = fields.Char(string="Tipo de Control", required=True)
    control_item = fields.Char(string="Ítem de Control", required=True)
    sequence = fields.Integer(string="Secuencia", default=10, required=True)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        (
            "checklist_item_unique",
            "unique(checklist_type, control_type, control_item)",
            "El ítem de control ya existe para este tipo de checklist.",
        )
    ]

    def name_get(self):
        return [
            (
                item.id,
                "%s / %s" % (item.control_type or "", item.control_item or ""),
            )
            for item in self
        ]


class BarcaMaintenanceChecklist(models.Model):
    _name = "barca.maintenance.checklist"
    _description = "Checklist"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "checklist_date desc, id desc"

    name = fields.Char(
        string="N° Checklist",
        required=True,
        copy=False,
        readonly=True,
        default="Nuevo",
        tracking=True,
    )
    requested_by_id = fields.Many2one(
        "res.users",
        string="Solicitante",
        default=lambda self: self.env.user,
        required=True,
        tracking=True,
    )
    vehicle_id = fields.Many2one(
        "fleet.vehicle",
        string="Equipo",
        required=True,
        tracking=True,
    )
    equipment_id = fields.Many2one(
        "maintenance.equipment",
        string="Equipo de mantenimiento",
        readonly=True,
        tracking=True,
    )
    checklist_date = fields.Date(
        string="Fecha",
        default=fields.Date.context_today,
        required=True,
        readonly=True,
        tracking=True,
    )
    detailed_location = fields.Text(
        string="Planta y lugar detallado",
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
    fuel_load_time = fields.Float(string="Hora carga combustible", tracking=True)
    odometer = fields.Float(string="Odómetro", tracking=True)
    observations = fields.Text(string="Observaciones", tracking=True)
    checklist_type = fields.Selection(
        CHECKLIST_TYPE_SELECTION,
        string="Tipo de vehículo",
        required=True,
        tracking=True,
    )
    line_ids = fields.One2many(
        "barca.maintenance.checklist.line",
        "checklist_id",
        string="Puntos de control",
        copy=True,
    )
    alert_id = fields.Many2one(
        "barca.maintenance.alert",
        string="Aviso vinculado",
        readonly=True,
        copy=False,
    )
    state = fields.Selection(
        [
            ("new", "Nuevo"),
            ("notice_created", "Aviso generado"),
            ("closed_no_notice", "Cerrado sin aviso"),
            ("cancelled", "Cancelado"),
        ],
        string="Estado",
        default="new",
        required=True,
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
                    "del checklist."
                )

    @api.onchange("vehicle_id")
    def _onchange_vehicle_id_set_equipment(self):
        for record in self:
            if record.vehicle_id:
                record.equipment_id = record._get_equipment_for_vehicle(record.vehicle_id.id)
            else:
                record.equipment_id = False

    @api.onchange("checklist_type")
    def _onchange_checklist_type_generate_lines(self):
        for record in self:
            if record.checklist_type:
                had_answers = any(line.yes or line.no for line in record.line_ids)
                record.line_ids = [(5, 0, 0)] + record._prepare_line_commands(
                    record.checklist_type
                )
                if had_answers:
                    return {
                        "warning": {
                            "title": "Puntos de control regenerados",
                            "message": (
                                "Se limpiaron las respuestas anteriores para evitar "
                                "mezclar líneas de distintos tipos de vehículo."
                            ),
                        }
                    }
            else:
                record.line_ids = [(5, 0, 0)]

    @api.model_create_multi
    def create(self, vals_list):
        equipment_by_vehicle = {}
        for vals in vals_list:
            vals["checklist_date"] = fields.Date.context_today(self)
            vals["line_ids"] = self._sanitize_line_commands(vals.get("line_ids"))
            if vals.get("name", "Nuevo") == "Nuevo":
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code("barca.maintenance.checklist")
                    or "Nuevo"
                )
            vehicle_id = vals.get("vehicle_id")
            if vehicle_id:
                if vehicle_id not in equipment_by_vehicle:
                    equipment_by_vehicle[vehicle_id] = self._get_equipment_for_vehicle(
                        vehicle_id
                    ).id
                vals["equipment_id"] = equipment_by_vehicle[vehicle_id] or False
        records = super().create(vals_list)
        for record in records:
            if record.checklist_type and not record.line_ids:
                record._generate_lines_from_type()
        return records

    def write(self, vals):
        vals = dict(vals)
        vals.pop("checklist_date", None)
        vals.pop("equipment_id", None)

        if "line_ids" in vals:
            vals["line_ids"] = self._sanitize_line_commands(vals.get("line_ids"))

        checklist_type_changed = "checklist_type" in vals
        if checklist_type_changed:
            for record in self:
                if record.state != "new":
                    raise ValidationError(
                        "Solo se puede cambiar el tipo de vehículo en estado Nuevo."
                    )

        if vals.get("vehicle_id"):
            equipment = self._get_equipment_for_vehicle(vals["vehicle_id"])
            vals["equipment_id"] = equipment.id

        result = super().write(vals)
        if checklist_type_changed:
            for record in self:
                record._generate_lines_from_type()
        return result


    def _sanitize_line_commands(self, commands):
        """Discard empty inline rows and complete generated line values.

        In editable one2many lists, the web client can send a create command for
        the placeholder row even when the user did not create a real checklist
        point. That empty command used to hit required readonly fields on
        `barca.maintenance.checklist.line` and raised the error reported in the
        UI for `control_type`. Checklist lines must come from the item catalog,
        so empty create commands are ignored and template-based commands are
        completed from the catalog before saving.
        """
        sanitized_commands = []
        for command in commands or []:
            if not isinstance(command, (list, tuple)) or not command:
                sanitized_commands.append(command)
                continue

            operation = command[0]
            if operation != 0:
                sanitized_commands.append(command)
                continue

            values = dict(command[2] or {}) if len(command) > 2 else {}
            if not any(
                values.get(field_name)
                for field_name in ("item_template_id", "control_type", "control_item")
            ):
                continue

            item = self.env["barca.maintenance.checklist.item"]
            item_template_id = values.get("item_template_id")
            if item_template_id:
                item = self.env["barca.maintenance.checklist.item"].browse(
                    item_template_id
                )
            if item:
                values.setdefault("control_type", item.control_type)
                values.setdefault("control_item", item.control_item)
                values.setdefault("sequence", item.sequence)

            sanitized_commands.append((0, 0, values))
        return sanitized_commands

    def _get_equipment_for_vehicle(self, vehicle_id):
        if not vehicle_id:
            return self.env["maintenance.equipment"]
        return self.env["maintenance.equipment"].search(
            [("vehicle_id", "=", vehicle_id)],
            limit=1,
        )

    def _prepare_line_commands(self, checklist_type):
        items = self.env["barca.maintenance.checklist.item"].search(
            [("checklist_type", "=", checklist_type), ("active", "=", True)]
        )
        return [
            (
                0,
                0,
                {
                    "item_template_id": item.id,
                    "control_type": item.control_type,
                    "control_item": item.control_item,
                    "sequence": item.sequence,
                },
            )
            for item in items
        ]

    def _generate_lines_from_type(self):
        for record in self:
            record.line_ids.unlink()
            if record.checklist_type:
                commands = record._prepare_line_commands(record.checklist_type)
                if commands:
                    record.write({"line_ids": commands})

    def _has_negative_answers(self):
        self.ensure_one()
        return any(line.no for line in self.line_ids)

    def _prepare_origin_note(self):
        self.ensure_one()
        origin_lines = [
            "Checklist %s creado por %s." % (self.name, self.requested_by_id.name)
        ]
        if self.detailed_location:
            origin_lines.append("Planta y lugar detallado: %s" % self.detailed_location)
        if self.vehicle_status:
            status_label = dict(self._fields["vehicle_status"].selection).get(
                self.vehicle_status,
                self.vehicle_status,
            )
            origin_lines.append("Estado del vehículo: %s" % status_label)
        if self.checklist_type:
            type_label = dict(self._fields["checklist_type"].selection).get(
                self.checklist_type,
                self.checklist_type,
            )
            origin_lines.append("Tipo de vehículo: %s" % type_label)
        if self.fuel_load_time:
            origin_lines.append("Hora carga combustible: %.2f" % self.fuel_load_time)
        if self.odometer:
            origin_lines.append("Odómetro: %.2f" % self.odometer)
        return "\n".join(origin_lines)

    def action_create_alert(self):
        created_alerts = self.env["barca.maintenance.alert"]
        for checklist in self:
            if checklist.state != "new":
                checklist.message_post(
                    body="Intento de generar aviso bloqueado: el checklist no está en estado Nuevo."
                )
                raise ValidationError(
                    "Solo se puede generar un aviso desde un checklist en estado Nuevo."
                )
            if checklist.alert_id:
                checklist.message_post(
                    body="Intento de generar aviso duplicado bloqueado."
                )
                raise ValidationError("El checklist ya tiene un aviso generado.")
            if not checklist._has_negative_answers():
                raise ValidationError(
                    "No hay puntos marcados como No. Use Cerrar sin aviso si corresponde."
                )
            if not checklist.observations:
                raise ValidationError(
                    "Debe completar Observaciones para describir la falla antes de generar el aviso."
                )

            alert_vals = {
                "source_type": "checklist",
                "source_reference": checklist.name,
                "checklist_id": checklist.id,
                "vehicle_id": checklist.vehicle_id.id,
                "equipment_id": checklist.equipment_id.id,
                "priority": "medium",
                "description": checklist.observations,
                "origin_note": checklist._prepare_origin_note(),
                "odometer": checklist.odometer,
            }
            alert = self.env["barca.maintenance.alert"].create(alert_vals)
            checklist.write({"alert_id": alert.id, "state": "notice_created"})
            checklist.message_post(body="Aviso generado: %s" % alert.name)
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

    def action_close_no_notice(self):
        for checklist in self:
            if checklist.state != "new":
                raise ValidationError(
                    "Solo se puede cerrar sin aviso un checklist en estado Nuevo."
                )
            if checklist._has_negative_answers():
                checklist.message_post(
                    body="Intento de cierre sin aviso bloqueado: existe al menos un punto marcado como No."
                )
                raise ValidationError(
                    "Existe al menos un punto marcado como No; corresponde generar un aviso."
                )
            checklist.write({"state": "closed_no_notice"})
            checklist.message_post(body="Checklist cerrado sin aviso.")

    def action_cancel(self):
        for checklist in self:
            if checklist.alert_id:
                raise ValidationError(
                    "No se puede cancelar un checklist que ya generó un aviso."
                )
            if checklist.state != "new":
                raise ValidationError("Solo se puede cancelar un checklist en estado Nuevo.")
            checklist.write({"state": "cancelled"})
            checklist.message_post(body="Checklist cancelado.")

    def action_view_alert(self):
        self.ensure_one()
        if not self.alert_id:
            raise ValidationError("El checklist no tiene un aviso generado.")
        return {
            "type": "ir.actions.act_window",
            "name": "Aviso vinculado",
            "res_model": "barca.maintenance.alert",
            "view_mode": "form",
            "views": [(False, "form")],
            "res_id": self.alert_id.id,
            "target": "current",
        }


class BarcaMaintenanceChecklistLine(models.Model):
    _name = "barca.maintenance.checklist.line"
    _description = "Línea de Checklist"
    _order = "sequence, id"

    checklist_id = fields.Many2one(
        "barca.maintenance.checklist",
        string="Checklist",
        required=True,
        ondelete="cascade",
        index=True,
    )
    item_template_id = fields.Many2one(
        "barca.maintenance.checklist.item",
        string="Ítem de control origen",
        ondelete="set null",
    )
    control_type = fields.Char(string="Tipo de Control", readonly=True)
    control_item = fields.Char(string="Ítem de Control", readonly=True)
    yes = fields.Boolean(string="Sí")
    no = fields.Boolean(string="No")
    sequence = fields.Integer(string="Secuencia", default=10)

    @api.onchange("yes")
    def _onchange_yes(self):
        for line in self:
            if line.yes:
                line.no = False

    @api.onchange("no")
    def _onchange_no(self):
        for line in self:
            if line.no:
                line.yes = False

    @api.constrains("yes", "no")
    def _check_yes_no_exclusive(self):
        for line in self:
            if line.yes and line.no:
                raise ValidationError(
                    "Una línea de checklist no puede tener Sí y No marcados al mismo tiempo."
                )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("yes"):
                vals["no"] = False
            if vals.get("no"):
                vals["yes"] = False
        return super().create(vals_list)

    def write(self, vals):
        vals = dict(vals)
        if vals.get("yes"):
            vals["no"] = False
        if vals.get("no"):
            vals["yes"] = False
        return super().write(vals)
