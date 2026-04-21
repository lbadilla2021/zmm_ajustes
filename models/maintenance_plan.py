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

    plan_line_ids = fields.One2many(
        "barca.maintenance.plan.line",
        "plan_id",
        string="Actividades del plan",
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
    # Helpers: vehículos del plan
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

    # -------------------------------------------------------------------------
    # Helpers: lectura de medidores del vehículo
    # -------------------------------------------------------------------------

    @staticmethod
    def _get_vehicle_km(vehicle):
        """Odómetro real actual del vehículo (campo estándar de flota)."""
        if "odometer" in vehicle._fields:
            return vehicle.odometer or 0.0
        return 0.0

    @staticmethod
    def _get_vehicle_hours(vehicle):
        """Horas de operación reales del vehículo."""
        for fname in ("x_operating_hours", "operating_hours", "hours_meter"):
            if fname in vehicle._fields:
                return vehicle[fname] or 0.0
        return 0.0

    @staticmethod
    def _get_vehicle_last_service_km(vehicle):
        """KM del último servicio registrado en el vehículo."""
        if "x_odometer_last_service" in vehicle._fields:
            return vehicle.x_odometer_last_service or 0.0
        return 0.0

    @staticmethod
    def _get_vehicle_last_service_date(vehicle):
        """Fecha del último servicio (salida de taller) del vehículo."""
        if "x_last_exit_date" in vehicle._fields and vehicle.x_last_exit_date:
            return vehicle.x_last_exit_date
        return None

    @staticmethod
    def _get_vehicle_last_service_hours(vehicle):
        """Horas de operación en el último servicio registrado."""
        if "x_hours_last_service" in vehicle._fields:
            return vehicle.x_hours_last_service or 0.0
        return 0.0

    # -------------------------------------------------------------------------
    # Lógica de trigger por vehículo
    # -------------------------------------------------------------------------

    def _should_generate_alert(self, vehicle, today):
        """
        Evalúa si el vehículo debe recibir un aviso para este plan.

        Regla km:
          - Con historial (last_service_km > 0):
              próximo_km = last_service_km + trigger_km
          - Primera vez (last_service_km == 0):
              próximo_km = trigger_km   (compara directo contra valor absoluto)
          - Dispara si: odómetro_real >= próximo_km - advance_km

        Regla días:
          - base = x_last_exit_date del vehículo, o hoy si nunca salió de taller
          - Dispara si: today >= base + trigger_days - advance_days

        Regla horas:
          - Con historial (last_service_hours > 0):
              próximo_hrs = last_service_hours + trigger_hours
          - Primera vez: próximo_hrs = trigger_hours
          - Dispara si: horas_reales >= próximo_hrs

        Lógica combinada: OR — basta con que se cumpla cualquier trigger activo.
        """
        self.ensure_one()
        km_triggered = False
        days_triggered = False
        hours_triggered = False

        # ── Trigger km ──────────────────────────────────────────────────────
        if self.trigger_km:
            current_km = self._get_vehicle_km(vehicle)
            last_service_km = self._get_vehicle_last_service_km(vehicle)

            next_km = (last_service_km + self.trigger_km) if last_service_km > 0 \
                else self.trigger_km
            threshold_km = next_km - (self.advance_km or 0.0)
            km_triggered = current_km >= threshold_km

            _logger.debug(
                "Plan '%s' | '%s' | km: real=%.0f last_svc=%.0f next=%.0f "
                "threshold=%.0f → %s",
                self.name, vehicle.name, current_km, last_service_km,
                next_km, threshold_km, km_triggered,
            )

        # ── Trigger días ─────────────────────────────────────────────────────
        if self.trigger_days:
            base_date = self._get_vehicle_last_service_date(vehicle) or today
            next_date = base_date + timedelta(
                days=self.trigger_days - (self.advance_days or 0)
            )
            days_triggered = today >= next_date

            _logger.debug(
                "Plan '%s' | '%s' | días: base=%s next=%s today=%s → %s",
                self.name, vehicle.name, base_date, next_date, today, days_triggered,
            )

        # ── Trigger horas ────────────────────────────────────────────────────
        if self.trigger_hours:
            current_hours = self._get_vehicle_hours(vehicle)
            last_service_hours = self._get_vehicle_last_service_hours(vehicle)

            next_hours = (last_service_hours + self.trigger_hours) \
                if last_service_hours > 0 else self.trigger_hours
            hours_triggered = current_hours >= next_hours

            _logger.debug(
                "Plan '%s' | '%s' | horas: real=%.1f last_svc=%.1f next=%.1f → %s",
                self.name, vehicle.name, current_hours, last_service_hours,
                next_hours, hours_triggered,
            )

        return km_triggered or days_triggered or hours_triggered

    # -------------------------------------------------------------------------
    # Constructores de valores para aviso
    # -------------------------------------------------------------------------

    def _build_alert_vals(self, vehicle, equipment):
        self.ensure_one()
        return {
            "source_type": "pm",
            "pm_id": self.id,
            "vehicle_id": vehicle.id,
            "equipment_id": equipment.id if equipment else False,
            "priority": "medium",
            "odometer": self._get_vehicle_km(vehicle),
            "operating_hours": self._get_vehicle_hours(vehicle),
            "alert_date": fields.Datetime.now(),
            "description": "Aviso generado automáticamente desde PM: %s" % self.name,
        }

    def _build_alert_line_vals(self, alert_id):
        self.ensure_one()
        return [
            {
                "alert_id": alert_id,
                "plan_line_id": line.id,
                "activity_id": line.activity_id.id,
                "technical_location_id": line.technical_location_id.id,
                "intervention_type_id": line.intervention_type_id.id,
                "estimated_duration": line.estimated_duration,
                "note": line.note,
                "sequence": line.sequence,
            }
            for line in self.plan_line_ids
        ]

    # -------------------------------------------------------------------------
    # Creación de un aviso para un vehículo concreto
    # -------------------------------------------------------------------------

    def _create_alert_for_vehicle(self, Alert, AlertLine, Equipment,
                                   vehicle, counters):
        """
        Intenta crear un aviso para el par (plan, vehículo).
        Retorna True si se creó, False en cualquier caso de omisión.
        """
        self.ensure_one()

        if self.trigger_km and not self._get_vehicle_km(vehicle):
            return False

        if not self._should_generate_alert(vehicle, fields.Date.today()):
            return False

        # Un vehículo no puede tener más de un aviso PM abierto,
        # independientemente del plan que lo originó.
        duplicate_domain = [
            ("source_type", "=", "pm"),
            ("vehicle_id", "=", vehicle.id),
            ("state", "not in", ["closed", "rejected"]),
        ]
        if Alert.search_count(duplicate_domain):
            counters["duplicated"] += 1
            _logger.info(
                "Plan '%s' | '%s' omitido: ya existe aviso abierto.",
                self.name, vehicle.name,
            )
            return False

        equipment = Equipment.search([("vehicle_id", "=", vehicle.id)], limit=1)
        alert = Alert.create(self._build_alert_vals(vehicle, equipment))
        AlertLine.create(self._build_alert_line_vals(alert.id))

        counters["created"] += 1
        _logger.info("Aviso creado: plan='%s' vehículo='%s'", self.name, vehicle.name)
        return True

    # -------------------------------------------------------------------------
    # Ejecución manual (botón en formulario)
    # -------------------------------------------------------------------------

    def _evaluate_and_generate_alerts(self):
        Alert = self.env["barca.maintenance.alert"]
        AlertLine = self.env["barca.maintenance.alert.line"]
        Equipment = self.env["maintenance.equipment"]
        counters = {"created": 0, "duplicated": 0, "skipped": 0}

        for plan in self:
            if not plan.plan_line_ids:
                _logger.warning("Plan '%s' sin líneas de actividad, se omite.", plan.name)
                counters["skipped"] += 1
                continue
            for vehicle in plan._get_plan_vehicles():
                plan._create_alert_for_vehicle(
                    Alert, AlertLine, Equipment, vehicle, counters
                )

        return counters

    def action_generate_alerts(self):
        result = self._evaluate_and_generate_alerts()
        created = result.get("created", 0)
        duplicated = result.get("duplicated", 0)
        msg = "Avisos generados: %d" % created
        if duplicated:
            msg += " | Ya existían: %d" % duplicated
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Generación de avisos",
                "message": msg,
                "type": "success" if created else "warning",
                "sticky": False,
            },
        }

    # -------------------------------------------------------------------------
    # Ejecución programada (cron) — orden creciente de triggers
    # -------------------------------------------------------------------------

    @api.model
    def run_pm_scheduler(self):
        """
        El orden trigger_km asc, trigger_days asc, trigger_hours asc garantiza
        que el plan de menor intervalo se evalúa primero para cada vehículo.
        Cuando ese plan genera un aviso abierto, los planes de mayor intervalo
        para el mismo vehículo quedan bloqueados por el control de duplicado
        hasta que el aviso sea cerrado o rechazado.
        """
        plans = self.search(
            [("active", "=", True)],
            order="trigger_km asc, trigger_days asc, trigger_hours asc",
        )
        _logger.info("Cron PM: %s planes activos.", len(plans))

        Alert = self.env["barca.maintenance.alert"]
        AlertLine = self.env["barca.maintenance.alert.line"]
        Equipment = self.env["maintenance.equipment"]
        counters = {"created": 0, "duplicated": 0, "skipped": 0}

        for plan in plans:
            if not plan.plan_line_ids:
                counters["skipped"] += 1
                continue
            for vehicle in plan._get_plan_vehicles():
                plan._create_alert_for_vehicle(
                    Alert, AlertLine, Equipment, vehicle, counters
                )

        _logger.info(
            "Cron PM finalizado. Creados: %s | Duplicados: %s | Omitidos: %s",
            counters["created"], counters["duplicated"], counters["skipped"],
        )
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
