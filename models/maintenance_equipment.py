from odoo import fields, models


class MaintenanceEquipment(models.Model):
    _inherit = "maintenance.equipment"

    vehicle_id = fields.Many2one(
        "fleet.vehicle",
        string="Vehículo",
        ondelete="cascade",
    )
    x_odometer_last_service = fields.Float(
        string="Odómetro último servicio",
        related="vehicle_id.x_odometer_last_service",
        readonly=True,
    )
    x_hours_last_service = fields.Float(
        string="Horas operación último servicio",
        related="vehicle_id.x_hours_last_service",
        readonly=True,
    )
    x_last_entry_date = fields.Date(
        string="Última entrada a taller",
        related="vehicle_id.x_last_entry_date",
        readonly=True,
    )
    x_last_exit_date = fields.Date(
        string="Última salida a taller",
        related="vehicle_id.x_last_exit_date",
        readonly=True,
    )
    x_current_odometer = fields.Float(
        string="Último odómetro",
        related="vehicle_id.odometer",
        readonly=True,
    )
    x_current_operating_hours = fields.Float(
        string="Horas de operación",
        related="vehicle_id.x_operating_hours",
        readonly=True,
    )

    x_doc_circulation_permit_expiry = fields.Date(
        string="Vencimiento permiso de circulación",
        related="vehicle_id.x_doc_circulation_permit_expiry",
        readonly=True,
    )
    x_doc_technical_review_expiry = fields.Date(
        string="Vencimiento revisión técnica",
        related="vehicle_id.x_doc_technical_review_expiry",
        readonly=True,
    )
    x_doc_fuel_card = fields.Char(
        string="Tarjeta combustible",
        related="vehicle_id.x_doc_fuel_card",
        readonly=True,
    )
    x_doc_tag = fields.Boolean(
        string="TAG",
        related="vehicle_id.x_doc_tag",
        readonly=True,
    )
    x_alert_days_before = fields.Integer(
        string="Días alerta vencimiento",
        related="vehicle_id.x_alert_days_before",
        readonly=True,
    )




    fleet_vehicle_model_year = fields.Char(
        string="Año del modelo",
        related="vehicle_id.model_year",
        readonly=False,
    )
    fleet_vehicle_transmission = fields.Selection(
        related="vehicle_id.transmission",
        string="Transmisión",
        readonly=False,
    )
    fleet_vehicle_color = fields.Char(
        string="Color",
        related="vehicle_id.color",
        readonly=False,
    )
    fleet_vehicle_seats = fields.Integer(
        string="Número de asientos",
        related="vehicle_id.seats",
        readonly=False,
    )
    fleet_vehicle_doors = fields.Integer(
        string="Número de puertas",
        related="vehicle_id.doors",
        readonly=False,
    )
    fleet_vehicle_trailer_hook = fields.Boolean(
        string="Enganche de remolque",
        related="vehicle_id.trailer_hook",
        readonly=False,
    )
    fleet_vehicle_power_unit = fields.Selection(
        related="vehicle_id.power_unit",
        string="Unidad de potencia",
        readonly=False,
    )
    # fleet.vehicle.power es Integer en Fleet. En un campo related, el tipo
    # debe coincidir exactamente con el campo origen; si se define como Float
    # Odoo no puede cargar el registry y devuelve Internal Server Error 500.
    fleet_vehicle_power = fields.Integer(
        string="Potencia",
        related="vehicle_id.power",
        readonly=False,
    )
    # En Fleet, el rango normalmente es numérico. No se usa related directo para
    # mantener compatibilidad con distintas versiones/nombres técnicos del campo.
    fleet_vehicle_range = fields.Integer(
        string="Rango",
        compute="_compute_fleet_vehicle_range",
        inverse="_inverse_fleet_vehicle_range",
    )
    fleet_vehicle_fuel_type = fields.Selection(
        related="vehicle_id.fuel_type",
        string="Tipo de combustible",
        readonly=False,
    )
    fleet_vehicle_co2 = fields.Float(
        string="Emisiones de CO2",
        related="vehicle_id.co2",
        readonly=False,
    )
    fleet_vehicle_co2_standard = fields.Char(
        string="Estándar de CO2",
        related="vehicle_id.co2_standard",
        readonly=False,
    )

    fleet_vehicle_model_id = fields.Many2one(
        "fleet.vehicle.model",
        string="Modelo",
        related="vehicle_id.model_id",
        readonly=False,
    )
    fleet_vehicle_vin_sn = fields.Char(
        string="N° chasis",
        related="vehicle_id.vin_sn",
        readonly=False,
    )
    fleet_vehicle_engine_code = fields.Char(
        string="Número de Motor",
        related="vehicle_id.x_engine_code",
        readonly=False,
    )


    def _compute_fleet_vehicle_range(self):
        candidate_fields = ("range", "electric_range", "range_km")
        for rec in self:
            rec.fleet_vehicle_range = 0
            vehicle = rec.vehicle_id
            if not vehicle:
                continue
            for field_name in candidate_fields:
                if field_name in vehicle._fields:
                    value = vehicle[field_name]
                    rec.fleet_vehicle_range = int(value or 0)
                    break

    def _inverse_fleet_vehicle_range(self):
        candidate_fields = ("range", "electric_range", "range_km")
        for rec in self:
            vehicle = rec.vehicle_id
            if not vehicle:
                continue
            for field_name in candidate_fields:
                if field_name in vehicle._fields:
                    vehicle[field_name] = int(rec.fleet_vehicle_range or 0)
                    break

    _sql_constraints = [
        (
            "unique_vehicle_equipment",
            "unique(vehicle_id)",
            "Ya existe un equipo de mantenimiento para este vehículo.",
        )
    ]
