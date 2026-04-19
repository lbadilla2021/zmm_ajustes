from odoo import models


class MaintenanceRequest(models.Model):
    _inherit = "maintenance.request"

    def write(self, vals):
        result = super().write(vals)
        tracked_fields = {"stage_id", "close_date", "kanban_state", "maintenance_status"}
        if tracked_fields.intersection(vals):
            finished_requests = self.filtered(
                lambda req: req.stage_id and req.stage_id.fold
            )
            if finished_requests:
                alerts = self.env["barca.maintenance.alert"].search(
                    [
                        ("maintenance_request_id", "in", finished_requests.ids),
                        ("state", "=", "in_progress"),
                    ]
                )
                if alerts:
                    alerts.action_review()
        return result
