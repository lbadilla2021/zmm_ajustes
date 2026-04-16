from odoo import api, fields, models
from odoo.exceptions import ValidationError


class BarcaMaintenancePlan(models.Model):
    _name = "barca.maintenance.plan"
    _description = "Plan de mantención preventiva"

    name = fields.Char(string="Nombre del plan", required=True)

    category_id = fields.Many2one(
        "fleet.vehicle.model.category",
        string="Categoría",
    )

    vehicle_ids = fields.Many2many(
        "fleet.vehicle",
        string="Vehículos específicos",
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
    def _check_plan_scope(self):
        for record in self:
            if not record.category_id and not record.vehicle_ids:
                raise ValidationError(
                    "Debe definir al menos una categoría o vehículos específicos para el plan."
                )

    @api.constrains("trigger_km", "trigger_days", "trigger_hours")
    def _check_triggers(self):
        for record in self:
            if (
                not record.trigger_km
                and not record.trigger_days
                and not record.trigger_hours
            ):
                raise ValidationError(
                    "Debe definir al menos un trigger: km, días u horas."
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
