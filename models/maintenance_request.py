from odoo import models


class MaintenanceRequest(models.Model):
    _inherit = "maintenance.request"

    # La OT gestiona su propio ciclo de programación, ejecución, revisión y cierre.
    # El aviso asociado permanece en "Con OT creada" hasta que el usuario lo cierre
    # explícitamente, una vez que la OT esté en una etapa terminada.

    pass
