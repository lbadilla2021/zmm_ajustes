from odoo import fields, models


class FleetVehicleLogContract(models.Model):
    _inherit = "fleet.vehicle.log.contract"

    attachment_ids = fields.Many2many(
        "ir.attachment",
        "fleet_vehicle_log_contract_ir_attachment_rel",
        "contract_id",
        "attachment_id",
        string="Adjuntos",
        copy=False,
    )
