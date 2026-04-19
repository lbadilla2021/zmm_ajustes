from odoo import fields, models


class BarcaMaintenanceTask(models.Model):
    _name = "barca.maintenance.task"
    _description = "Actividad de mantención"
    _order = "code, name"

    _sql_constraints = [
        (
            "unique_barca_maintenance_task_code",
            "unique(code)",
            "Ya existe una actividad con el mismo código.",
        )
    ]

    name = fields.Char(string="Nombre", required=True)
    code = fields.Char(string="Código", required=True, index=True)
    location_id = fields.Many2one(
        "barca.technical.location",
        string="Ubicación técnica",
        required=True,
    )
    intervention_type_id = fields.Many2one(
        "barca.intervention.type",
        string="Tipo de intervención",
        required=True,
    )
    description = fields.Text(string="Descripción")
    active = fields.Boolean(default=True)
