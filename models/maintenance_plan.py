import logging
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError


_logger = logging.getLogger(__name__)


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

    company_id = fields.Many2one(
        "res.company",
        string="Compañía",
        default=lambda self: self.env.company,
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

    last_execution_date = fields.Date(string="Última ejecución")
    last_execution_km = fields.Float(string="KM última ejecución")
    last_execution_hours = fields.Float(string="Horas última ejecución")

    advance_km = fields.Float(string="Aviso anticipado km")
    advance_days = fields.Integer(string="Aviso anticipado días")

    kit_id = fields.Many2one(
        "barca.maintenance.kit",
        string="Kit sugerido",
    )

    active = fields.Boolean(default=True)

    def _get_plan_vehicles(self):
        self.ensure_one()
        vehicles = self.vehicle_ids
        if self.category_id:
            category_vehicles = self.env["fleet.vehicle"].search(
                [("category_id", "=", self.category_id.id)]
            )
            vehicles |= category_vehicles
        return vehicles

    def _get_vehicle_operating_hours(self, vehicle):
        for field_name in ("operating_hours", "x_operating_hours", "hours_meter"):
            if field_name in vehicle._fields:
                return vehicle[field_name] or 0.0
        return None

    def _should_generate_alert(self, plan, vehicle, today):
        km_triggered = False
        days_triggered = False
        hours_triggered = False

        vehicle_km = vehicle.odometer if "odometer" in vehicle._fields else 0.0
        if plan.trigger_km:
            km_threshold = plan.trigger_km - (plan.advance_km or 0.0)
            km_triggered = vehicle_km >= km_threshold

        if plan.trigger_days:
            base_date = fields.Date.to_date(plan.last_execution_date or plan.create_date or today)
            days_threshold = base_date + timedelta(
                days=(plan.trigger_days - (plan.advance_days or 0))
            )
            days_triggered = today >= days_threshold

        if plan.trigger_hours:
            vehicle_hours = plan._get_vehicle_operating_hours(vehicle)
            if vehicle_hours is not None:
                hours_threshold = plan.trigger_hours
                hours_triggered = vehicle_hours >= hours_threshold

        return km_triggered or days_triggered or hours_triggered

    def _evaluate_and_generate_alerts(self):
        Alert = self.env["barca.maintenance.alert"]
        Equipment = self.env["maintenance.equipment"]
        today = fields.Date.today()

        counters = {"created": 0, "duplicated": 0}
        _logger.info("Evaluando planes de mantenimiento")
        _logger.info("Inicio evaluación PM para %s plan(es).", len(self))

        for plan in self:
            _logger.info("Procesando plan: %s", plan.name)
            vehicles = plan._get_plan_vehicles()
            for vehicle in vehicles:
                if plan.trigger_km and not vehicle.odometer:
                    continue

                if not plan._should_generate_alert(plan, vehicle, today):
                    continue

                duplicate_domain = [
                    ("source_type", "=", "pm"),
                    ("pm_id", "=", plan.id),
                    ("vehicle_id", "=", vehicle.id),
                    ("technical_location_id", "=", plan.technical_location_id.id),
                    ("intervention_type_id", "=", plan.intervention_type_id.id),
                    ("state", "not in", ["closed", "rejected"]),
                ]
                if Alert.search_count(duplicate_domain):
                    counters["duplicated"] += 1
                    _logger.info("Aviso omitido por duplicado")
                    continue

                equipment = Equipment.search([("vehicle_id", "=", vehicle.id)], limit=1)
                priority = "medium"
                if "priority" in plan._fields and plan.priority:
                    priority = plan.priority

                Alert.create(
                    {
                        "source_type": "pm",
                        "pm_id": plan.id,
                        "vehicle_id": vehicle.id,
                        "equipment_id": equipment.id or False,
                        "technical_location_id": plan.technical_location_id.id,
                        "intervention_type_id": plan.intervention_type_id.id,
                        "priority": priority,
                        "odometer": vehicle.odometer if "odometer" in vehicle._fields else 0.0,
                        "alert_date": fields.Datetime.now(),
                        "description": f"Aviso generado automáticamente desde PM: {plan.name}",
                    }
                )
                counters["created"] += 1
                _logger.info("Aviso creado para vehículo: %s", vehicle.name)

        _logger.info(
            "Evaluación PM finalizada. Planes: %s | Avisos creados: %s | Duplicados omitidos: %s",
            len(self),
            counters["created"],
            counters["duplicated"],
        )
        return counters

    def action_generate_alerts(self):
        self._evaluate_and_generate_alerts()
        return True

    @api.model
    def run_pm_scheduler(self):
        plans = self.search([("active", "=", True)])
        _logger.info("Ejecución programada PM. Planes activos detectados: %s", len(plans))
        plans._evaluate_and_generate_alerts()
        return True

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
