from odoo import models


class MaintenanceRequest(models.Model):
    _inherit = "maintenance.request"

    def write(self, vals):
        result = super().write(vals)
        tracked_fields = {"stage_id", "close_date", "kanban_state", "maintenance_status"}
        if tracked_fields.intersection(vals):
            finished_requests = self.filtered(
                lambda req: (
                    req.stage_id
                    and "done" in req.stage_id._fields
                    and req.stage_id.done
                )
                or bool(req.close_date)
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
