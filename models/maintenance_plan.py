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
            "unique_plan_name_category",
            "unique(name, category_id)",
            "Ya existe un plan con ese nombre para esta categoría.",
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

    company_id = fields.Many2one(
        "res.company",
        string="Compañía",
        default=lambda self: self.env.company,
    )

    # Líneas de actividades: el corazón del plan
    plan_line_ids = fields.One2many(
        "barca.maintenance.plan.line",
        "plan_id",
        string="Actividades del plan",
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

    # -------------------------------------------------------------------------
    # Campos computados de resumen (informativos en encabezado)
    # -------------------------------------------------------------------------

    line_count = fields.Integer(
        string="N° actividades",
        compute="_compute_line_count",
        store=True,
    )

    @api.depends("plan_line_ids")
    def _compute_line_count(self):
        for rec in self:
            rec.line_count = len(rec.plan_line_ids)

    # -------------------------------------------------------------------------
    # Lógica de vehículos y triggers
    # -------------------------------------------------------------------------

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
            base_date = fields.Date.to_date(
                plan.last_execution_date or plan.create_date or today
            )
            days_threshold = base_date + timedelta(
                days=(plan.trigger_days - (plan.advance_days or 0))
            )
            days_triggered = today >= days_threshold

        if plan.trigger_hours:
            vehicle_hours = plan._get_vehicle_operating_hours(vehicle)
            if vehicle_hours is not None:
                hours_triggered = vehicle_hours >= plan.trigger_hours

        return km_triggered or days_triggered or hours_triggered

    # -------------------------------------------------------------------------
    # Generación de avisos
    # -------------------------------------------------------------------------

    def _evaluate_and_generate_alerts(self):
        Alert = self.env["barca.maintenance.alert"]
        AlertLine = self.env["barca.maintenance.alert.line"]
        Equipment = self.env["maintenance.equipment"]
        today = fields.Date.today()

        counters = {"created": 0, "duplicated": 0}
        _logger.info("Evaluando planes de mantenimiento")
        _logger.info("Inicio evaluación PM para %s plan(es).", len(self))

        for plan in self:
            _logger.info("Procesando plan: %s", plan.name)

            if not plan.plan_line_ids:
                _logger.warning(
                    "Plan '%s' sin líneas de actividad definidas, se omite.", plan.name
                )
                continue

            vehicles = plan._get_plan_vehicles()
            for vehicle in vehicles:
                if plan.trigger_km and not vehicle.odometer:
                    continue

                if not plan._should_generate_alert(plan, vehicle, today):
                    continue

                # Usamos plan.id como referencia de duplicado (ya no hay
                # technical_location/intervention en encabezado)
                duplicate_domain = [
                    ("source_type", "=", "pm"),
                    ("pm_id", "=", plan.id),
                    ("vehicle_id", "=", vehicle.id),
                    ("state", "not in", ["closed", "rejected"]),
                ]
                if Alert.search_count(duplicate_domain):
                    counters["duplicated"] += 1
                    _logger.info("Aviso omitido por duplicado")
                    continue

                equipment = Equipment.search(
                    [("vehicle_id", "=", vehicle.id)], limit=1
                )
                priority = "medium"

                # Construir líneas del aviso a partir de las líneas del plan
                alert_line_vals = [
                    {
                        "plan_line_id": line.id,
                        "activity_id": line.activity_id.id,
                        "technical_location_id": line.technical_location_id.id,
                        "intervention_type_id": line.intervention_type_id.id,
                        "estimated_duration": line.estimated_duration,
                        "note": line.note,
                        "sequence": line.sequence,
                    }
                    for line in plan.plan_line_ids
                ]

                alert = Alert.create(
                    {
                        "source_type": "pm",
                        "pm_id": plan.id,
                        "vehicle_id": vehicle.id,
                        "equipment_id": equipment.id or False,
                        "priority": priority,
                        "odometer": vehicle.odometer
                        if "odometer" in vehicle._fields
                        else 0.0,
                        "alert_date": fields.Datetime.now(),
                        "description": (
                            "Aviso generado automáticamente desde PM: %s" % plan.name
                        ),
                    }
                )

                # Crear las líneas de actividad en el aviso
                for line_vals in alert_line_vals:
                    line_vals["alert_id"] = alert.id
                AlertLine.create(alert_line_vals)

                counters["created"] += 1
                _logger.info("Aviso creado para vehículo: %s", vehicle.name)

        _logger.info(
            "Evaluación PM finalizada. Planes: %s | Avisos creados: %s | "
            "Duplicados omitidos: %s",
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
        _logger.info(
            "Ejecución programada PM. Planes activos detectados: %s", len(plans)
        )
        plans._evaluate_and_generate_alerts()
        return True

    # -------------------------------------------------------------------------
    # Constrains
    # -------------------------------------------------------------------------

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
