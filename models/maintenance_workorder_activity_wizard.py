from collections import Counter, defaultdict

from odoo import Command, api, fields, models
from odoo.exceptions import ValidationError


class BarcaMaintenanceWorkorderActivitySelectionWizard(models.TransientModel):
    _name = "barca.maintenance.workorder.activity.selection.wizard"
    _description = "Selección múltiple de actividades para OT"

    maintenance_request_id = fields.Many2one(
        "maintenance.request",
        string="Orden de Trabajo",
        required=True,
        readonly=True,
    )

    vehicle_category_id = fields.Many2one(
        "fleet.vehicle.model.category",
        string="Categoría de Vehículos",
        related="maintenance_request_id.barca_vehicle_category_id",
        readonly=True,
    )
    vehicle_type = fields.Selection(
        related="maintenance_request_id.barca_vehicle_type",
        string="Tipo de vehículo",
        readonly=True,
    )

    selection_line_ids = fields.One2many(
        "barca.maintenance.workorder.activity.selection.wizard.line",
        "wizard_id",
        string="Actividades disponibles",
    )

    @api.model
    def _get_preferred_intervention_types(self, activities):
        """Propone el tipo más utilizado por actividad en los planes PM."""
        preferred = {}
        counters = defaultdict(Counter)
        plan_lines = self.env["barca.maintenance.plan.line"].search(
            [
                ("activity_id", "in", activities.ids),
                ("intervention_type_id", "!=", False),
            ]
        )
        for plan_line in plan_lines:
            counters[plan_line.activity_id.id][plan_line.intervention_type_id.id] += 1

        for activity_id, counter in counters.items():
            # En empates se usa el ID menor para mantener un resultado estable.
            preferred[activity_id] = max(
                counter.items(), key=lambda item: (item[1], -item[0])
            )[0]

        fallback = self.env["barca.intervention.type"].search(
            [("name", "=ilike", "Realizar")], limit=1
        )
        if fallback:
            for activity in activities:
                preferred.setdefault(activity.id, fallback.id)
        return preferred

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        request_id = (
            values.get("maintenance_request_id")
            or self.env.context.get("default_maintenance_request_id")
        )
        request = self.env["maintenance.request"].browse(request_id).exists()
        if not request or not request.barca_vehicle_category_id:
            return values

        activities = self.env["barca.maintenance.activity"].search(
            [
                ("active", "=", True),
                ("category_id", "=", request.barca_vehicle_category_id.id),
                ("technical_location_id.vehicle_type", "=", request.barca_vehicle_type),
                ("technical_location_id.level", "=", 0),
            ],
            order="technical_location_id, name, id",
        )
        preferred_types = self._get_preferred_intervention_types(activities)
        values["selection_line_ids"] = [
            Command.create(
                {
                    "activity_id": activity.id,
                    "intervention_type_id": preferred_types.get(activity.id),
                }
            )
            for activity in activities
        ]
        return values

    @api.model
    def _prepare_material_commands(self, activity):
        return [
            Command.create(
                {
                    "sequence": material.sequence,
                    "product_id": material.product_id.id,
                    "product_uom_id": material.product_uom_id.id,
                    "estimated_quantity": material.quantity,
                    "note": material.note,
                }
            )
            for material in activity.material_template_line_ids.sorted(
                lambda line: (line.sequence, line.id)
            )
        ]

    def action_add_activities(self):
        self.ensure_one()
        request = self.maintenance_request_id
        request._barca_check_can_add_activities()

        selected_lines = self.selection_line_ids.filtered("selected")
        if not selected_lines:
            raise ValidationError("Seleccione al menos una actividad.")

        incompatible = selected_lines.filtered(
            lambda line: (
                line.activity_id.category_id != self.vehicle_category_id
                or not line.activity_id.technical_location_id
                or line.activity_id.technical_location_id.vehicle_type
                != self.vehicle_type
                or line.activity_id.technical_location_id.level != 0
            )
        )
        if incompatible:
            raise ValidationError(
                "Existen actividades seleccionadas que no corresponden a la "
                "categoría y al tipo del vehículo de la OT, o cuya "
                "ubicación técnica no es de nivel 0."
            )

        missing_type = selected_lines.filtered(
            lambda line: not line.intervention_type_id
        )
        if missing_type:
            raise ValidationError(
                "Defina el Tipo de intervención para las actividades "
                "seleccionadas: %s."
                % ", ".join(missing_type.mapped("activity_id.display_name"))
            )

        next_sequence = max(
            request.barca_activity_line_ids.mapped("sequence") or [0]
        )
        vals_list = []
        for line in selected_lines.sorted(lambda record: record.id):
            activity = line.activity_id
            next_sequence += 10
            vals_list.append(
                {
                    "maintenance_request_id": request.id,
                    "sequence": next_sequence,
                    "technical_location_id": activity.technical_location_id.id,
                    "intervention_type_id": line.intervention_type_id.id,
                    "activity_id": activity.id,
                    "description": activity.note,
                    "estimated_duration": activity.estimated_duration,
                    "state": "pending",
                    "material_line_ids": self._prepare_material_commands(activity),
                }
            )

        self.env["barca.maintenance.workorder.line"].create(vals_list)
        return {"type": "ir.actions.act_window_close"}


class BarcaMaintenanceWorkorderActivitySelectionWizardLine(models.TransientModel):
    _name = "barca.maintenance.workorder.activity.selection.wizard.line"
    _description = "Actividad disponible para selección múltiple de OT"
    _order = "id"

    wizard_id = fields.Many2one(
        "barca.maintenance.workorder.activity.selection.wizard",
        required=True,
        ondelete="cascade",
    )
    selected = fields.Boolean(string="Seleccionar")
    activity_id = fields.Many2one(
        "barca.maintenance.activity",
        string="Actividad",
        required=True,
        readonly=True,
    )
    technical_location_id = fields.Many2one(
        "barca.technical.location",
        string="Ubicación técnica",
        related="activity_id.technical_location_id",
        readonly=True,
    )
    intervention_type_id = fields.Many2one(
        "barca.intervention.type",
        string="Tipo de intervención",
    )
    estimated_duration = fields.Float(
        string="Duración estimada (hrs)",
        related="activity_id.estimated_duration",
        readonly=True,
    )
    material_count = fields.Integer(
        string="N° materiales",
        related="activity_id.material_count",
        readonly=True,
    )
    material_summary = fields.Char(
        string="Materiales estándar",
        related="activity_id.material_summary",
        readonly=True,
    )
