from odoo import api, fields, models
from odoo.exceptions import ValidationError


class BarcaMaintenanceKit(models.Model):
    _name = "barca.maintenance.kit"
    _description = "Kit de mantención"
    _order = "name"

    _sql_constraints = [
        (
            "unique_maintenance_kit_code",
            "unique(code)",
            "Ya existe un kit con ese código.",
        )
    ]

    name = fields.Char(string="Nombre", required=True)
    code = fields.Char(string="Código")

    category_id = fields.Many2one(
        "fleet.vehicle.model.category",
        string="Categoría",
    )

    technical_location_id = fields.Many2one(
        "barca.technical.location",
        string="Ubicación técnica",
    )

    line_ids = fields.One2many(
        "barca.maintenance.kit.line",
        "kit_id",
        string="Líneas",
    )

    active = fields.Boolean(default=True)
    note = fields.Text(string="Notas")

    @api.constrains("category_id", "technical_location_id")
    def _check_technical_location_category(self):
        for record in self:
            if (
                record.category_id
                and record.technical_location_id.category_id
                and record.technical_location_id.category_id != record.category_id
            ):
                raise ValidationError(
                    "La categoría de la ubicación técnica debe coincidir con la categoría del kit."
                )


class BarcaMaintenanceKitLine(models.Model):
    _name = "barca.maintenance.kit.line"
    _description = "Línea de kit de mantención"
    _order = "id"

    kit_id = fields.Many2one(
        "barca.maintenance.kit",
        required=True,
        ondelete="cascade",
        string="Kit",
    )

    product_id = fields.Many2one(
        "product.product",
        required=True,
        string="Producto",
    )

    quantity = fields.Float(string="Cantidad", default=1.0, required=True)

    uom_id = fields.Many2one(
        "uom.uom",
        string="Unidad de medida",
    )

    note = fields.Char(string="Nota")

    @api.constrains("quantity")
    def _check_quantity(self):
        for record in self:
            if record.quantity <= 0:
                raise ValidationError("La cantidad debe ser mayor a cero.")
