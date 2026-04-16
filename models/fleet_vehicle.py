from odoo import api, fields, models


class FleetVehicle(models.Model):
    _inherit = "fleet.vehicle"

    # Identificación
    x_internal_code = fields.Char(string="Código interno")
    x_engine_code = fields.Char(string="Código motor")

    # Medición
    x_odometer_last_service = fields.Float(string="Odómetro último servicio")
    x_odometer_next_service = fields.Float(
        string="Próximo servicio (km)",
        compute="_compute_next_service",
        store=True,
    )
    x_operating_hours = fields.Float(string="Horas de operación")

    # Taller
    x_last_entry_date = fields.Date(string="Última entrada a taller")
    x_last_exit_date = fields.Date(string="Última salida a taller")
    x_downtime_total = fields.Float(
        string="Tiempo fuera de servicio (hrs)",
        compute="_compute_downtime",
        store=True,
    )

    # Documentación
    x_doc_circulation_permit_expiry = fields.Date(
        string="Vencimiento permiso de circulación"
    )
    x_doc_technical_review_expiry = fields.Date(
        string="Vencimiento revisión técnica"
    )
    x_doc_padron = fields.Char(string="Padrón")
    x_doc_fuel_card = fields.Char(string="Tarjeta combustible")
    x_doc_tag = fields.Char(string="TAG")
    x_alert_days_before = fields.Integer(string="Días alerta vencimiento", default=15)

    # Notas
    x_maintenance_note = fields.Text(string="Notas de mantención")

    @api.depends("x_odometer_last_service")
    def _compute_next_service(self):
        for vehicle in self:
            vehicle.x_odometer_next_service = vehicle.x_odometer_last_service + 5000.0

    @api.depends("x_last_entry_date", "x_last_exit_date")
    def _compute_downtime(self):
        for vehicle in self:
            vehicle.x_downtime_total = 0.0

    @api.model_create_multi
    def create(self, vals_list):
        vehicles = super().create(vals_list)
        equipment_model = self.env["maintenance.equipment"]

        existing_equipment = equipment_model.search(
            [("vehicle_id", "in", vehicles.ids)]
        ).mapped("vehicle_id")
        vehicles_without_equipment = vehicles - existing_equipment

        equipment_to_create = [
            {
                "name": vehicle.name,
                "vehicle_id": vehicle.id,
            }
            for vehicle in vehicles_without_equipment
        ]
        if equipment_to_create:
            equipment_model.create(equipment_to_create)

        return vehicles
