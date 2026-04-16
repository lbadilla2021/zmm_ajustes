from odoo import api, fields, models
from odoo.exceptions import ValidationError


class BarcaMaintenancePlan(models.Model):
    _name = "barca.maintenance.plan"
    _description = "Plan de mantención preventiva"
    _order = "name"

    _sql_constraints = [
        (
            "unique_plan_core_category",
            "unique(technical_location_id, intervention_type_id, category_id)",
            "Ya existe un plan por categoría con la misma ubicación técnica y tipo de intervención.",
        )
    ]

    name = fields.Char(string="Nombre del plan", required=True)

    category_id = fields.Many2one(
        "fleet.vehicle.model.category",
        string="Categoría",
        index=True,
    )

    vehicle_ids = fields.Many2many(
        "fleet.vehicle",
        string="Vehículos específicos",
    )

    technical_location_id = fields.Many2one(
        "barca.technical.location",
        string="Ubicación técnica",
        required=True,
        index=True,
    )

    intervention_type_id = fields.Many2one(
        "barca.intervention.type",
        string="Tipo de intervención",
        required=True,
        index=True,
    )

    trigger_km = fields.Float(string="Intervalo km")
    trigger_days = fields.Integer(string="Intervalo días")
    trigger_hours = fields.Float(string="Intervalo horas")

    advance_km = fields.Float(string="Aviso anticipado km")
    advance_days = fields.Integer(string="Aviso anticipado días")

    kit_id = fields.Many2one(
        "barca.maintenance.kit",
        string="Kit sugerido",
    )

    active = fields.Boolean(default=True)

    @api.constrains("category_id", "vehicle_ids")
    def _check_scope(self):
        for rec in self:
            if not rec.category_id and not rec.vehicle_ids:
                raise ValidationError(
                    "Debe definir una categoría o vehículos específicos."
                )

    @api.constrains("trigger_km", "trigger_days", "trigger_hours")
    def _check_triggers(self):
        for rec in self:
            if not rec.trigger_km and not rec.trigger_days and not rec.trigger_hours:
                raise ValidationError(
                    "Debe definir al menos un trigger: km, días o horas."
                )

    @api.constrains("trigger_km", "trigger_days", "trigger_hours")
    def _check_trigger_values(self):
        for rec in self:
            if rec.trigger_km and rec.trigger_km <= 0:
                raise ValidationError("El intervalo en km debe ser mayor a cero.")

            if rec.trigger_days and rec.trigger_days <= 0:
                raise ValidationError("El intervalo en días debe ser mayor a cero.")

            if rec.trigger_hours and rec.trigger_hours <= 0:
                raise ValidationError("El intervalo en horas debe ser mayor a cero.")

    @api.constrains("advance_km", "trigger_km", "advance_days", "trigger_days")
    def _check_advance_values(self):
        for rec in self:
            if rec.advance_km and rec.trigger_km:
                if rec.advance_km >= rec.trigger_km:
                    raise ValidationError(
                        "El aviso anticipado en km debe ser menor que el intervalo."
                    )

            if rec.advance_days and rec.trigger_days:
                if rec.advance_days >= rec.trigger_days:
                    raise ValidationError(
                        "El aviso anticipado en días debe ser menor que el intervalo."
                    )

    @api.constrains("category_id", "technical_location_id")
    def _check_technical_location_category(self):
        for record in self:
            if (
                record.category_id
                and record.technical_location_id.category_id
                and record.technical_location_id.category_id != record.category_id
            ):
                raise ValidationError(
                    "La categoría de la ubicación técnica debe coincidir con la categoría del plan."
                )

    @api.constrains(
        "technical_location_id",
        "intervention_type_id",
        "category_id",
        "vehicle_ids",
    )
    def _check_unique_plan_definition(self):
        for record in self:
            domain = [
                ("id", "!=", record.id),
                ("technical_location_id", "=", record.technical_location_id.id),
                ("intervention_type_id", "=", record.intervention_type_id.id),
            ]
            candidates = self.search(domain)
            record_vehicle_ids = set(record.vehicle_ids.ids)

            for candidate in candidates:
                same_category = (
                    record.category_id
                    and candidate.category_id
                    and record.category_id == candidate.category_id
                )
                shared_vehicle = bool(
                    record_vehicle_ids.intersection(candidate.vehicle_ids.ids)
                )

                if same_category or shared_vehicle:
                    raise ValidationError(
                        "Ya existe un plan con la misma ubicación técnica y tipo de intervención "
                        "que coincide por categoría o por vehículo."
                    )
