from collections import defaultdict

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class MaintenanceRequest(models.Model):
    _inherit = "maintenance.request"

    # La OT gestiona su propio ciclo de programacion, ejecucion, revision y cierre.
    # El aviso asociado se cierra automaticamente cuando la OT llega a una etapa
    # final Barca: Cierre Total, Cierre Parcial o Desechar.

    _BARCA_PROGRESS_STAGE_NAMES = ("En progreso", "In Progress")
    _BARCA_REVIEW_STAGE_NAMES = ("En revisión", "En revision")
    _BARCA_DISCARD_STAGE_NAMES = ("Desechar", "Scrap", "Discard")

    def _barca_find_stage(self, names=(), xmlids=()):
        Stage = self.env["maintenance.stage"]
        for xmlid in xmlids:
            stage = self.env.ref(xmlid, raise_if_not_found=False)
            if stage:
                return stage
        if names:
            stage = Stage.search([("name", "in", list(names))], order="sequence, id", limit=1)
            if stage:
                return stage
        return Stage.browse()

    @api.model
    def _barca_set_stage_xmlid(self, xmlid_name, stage):
        data = self.env["ir.model.data"].sudo()
        xmlid = data.search(
            [
                ("module", "=", "zmm_ajustes"),
                ("name", "=", xmlid_name),
                ("model", "=", "maintenance.stage"),
            ],
            limit=1,
        )
        vals = {
            "module": "zmm_ajustes",
            "name": xmlid_name,
            "model": "maintenance.stage",
            "res_id": stage.id,
            "noupdate": False,
        }
        if xmlid:
            xmlid.write({"res_id": stage.id, "noupdate": False})
        else:
            data.create(vals)

    @api.model
    def _barca_merge_stage(self, duplicate_stage, target_stage):
        if not duplicate_stage or not target_stage or duplicate_stage == target_stage:
            return
        self.search([("stage_id", "=", duplicate_stage.id)]).with_context(
            skip_barca_stage_transition=True
        ).write(
            {"stage_id": target_stage.id}
        )
        duplicate_stage.unlink()

    @api.model
    def _barca_sync_maintenance_stages(self):
        """Normaliza etapas globales para que la barra no duplique estados Barca."""
        Stage = self.env["maintenance.stage"].sudo()
        review_stage = Stage.search(
            [("name", "in", ["Reparado", "Repaired"])],
            order="sequence, id",
            limit=1,
        )
        if not review_stage:
            review_stage = Stage.search(
                [("name", "in", list(self._BARCA_REVIEW_STAGE_NAMES))],
                order="sequence, id",
                limit=1,
            )
        if not review_stage:
            review_stage = Stage.create(
                {
                    "name": "En revisión",
                    "sequence": 40,
                    "fold": False,
                    "done": False,
                }
            )
        review_stage.write(
            {
                "name": "En revisión",
                "sequence": 40,
                "fold": False,
                "done": False,
            }
        )
        self._barca_set_stage_xmlid("stage_barca_maintenance_review", review_stage)
        duplicate_reviews = Stage.search(
            [
                ("id", "!=", review_stage.id),
                ("name", "in", ["Reparado", "Repaired", "En revisión", "En revision"]),
            ]
        )
        for duplicate in duplicate_reviews:
            self._barca_merge_stage(duplicate, review_stage)

        discard_stage = Stage.search(
            [("name", "in", list(self._BARCA_DISCARD_STAGE_NAMES))],
            order="sequence, id",
            limit=1,
        )
        if not discard_stage:
            discard_stage = Stage.create(
                {
                    "name": "Desechar",
                    "sequence": 70,
                    "fold": True,
                    "done": True,
                }
            )
        discard_stage.write(
            {
                "name": "Desechar",
                "sequence": 70,
                "fold": True,
                "done": True,
            }
        )
        self._barca_set_stage_xmlid("stage_barca_maintenance_discard", discard_stage)
        duplicate_discards = Stage.search(
            [
                ("id", "!=", discard_stage.id),
                ("name", "in", list(self._BARCA_DISCARD_STAGE_NAMES)),
            ]
        )
        for duplicate in duplicate_discards:
            self._barca_merge_stage(duplicate, discard_stage)

        self.env["barca.maintenance.workorder.line"].sudo().search(
            [("state", "=", "closed")]
        ).write({"state": "notified"})

    def _barca_get_progress_stage(self):
        return self._barca_find_stage(names=self._BARCA_PROGRESS_STAGE_NAMES)

    def _barca_get_stage_in_progress(self):
        return self._barca_get_progress_stage()

    def _barca_get_review_stage(self):
        review_stage = self._barca_find_stage(
            xmlids=("zmm_ajustes.stage_barca_maintenance_review",),
            names=self._BARCA_REVIEW_STAGE_NAMES,
        )
        if review_stage:
            duplicate_reviews = self.env["maintenance.stage"].sudo().search(
                [
                    ("id", "!=", review_stage.id),
                    ("name", "in", ["Reparado", "Repaired"]),
                ]
            )
            for duplicate in duplicate_reviews:
                self._barca_merge_stage(duplicate, review_stage)
            return review_stage
        repaired_stage = self._barca_find_stage(names=("Reparado", "Repaired"))
        if repaired_stage:
            repaired_stage.sudo().write(
                {
                    "name": "En revisión",
                    "sequence": 40,
                    "fold": False,
                    "done": False,
                }
            )
            self._barca_set_stage_xmlid(
                "stage_barca_maintenance_review", repaired_stage
            )
            return repaired_stage
        return review_stage

    def _barca_get_stage_review(self):
        return self._barca_get_review_stage()

    def _barca_get_repaired_stage(self):
        return self._barca_get_review_stage()

    def _barca_get_close_total_stage(self):
        return self._barca_find_stage(
            xmlids=("zmm_ajustes.stage_barca_maintenance_close_total",),
            names=("Cierre Total",),
        )

    def _barca_get_stage_close_total(self):
        return self._barca_get_close_total_stage()

    def _barca_get_close_partial_stage(self):
        return self._barca_find_stage(
            xmlids=("zmm_ajustes.stage_barca_maintenance_close_partial",),
            names=("Cierre Parcial",),
        )

    def _barca_get_stage_close_partial(self):
        return self._barca_get_close_partial_stage()

    def _barca_get_discard_stage(self):
        discard_stage = self._barca_find_stage(
            xmlids=("zmm_ajustes.stage_barca_maintenance_discard",),
            names=self._BARCA_DISCARD_STAGE_NAMES,
        )
        if discard_stage:
            duplicate_discards = self.env["maintenance.stage"].sudo().search(
                [
                    ("id", "!=", discard_stage.id),
                    ("name", "in", list(self._BARCA_DISCARD_STAGE_NAMES)),
                ]
            )
            for duplicate in duplicate_discards:
                self._barca_merge_stage(duplicate, discard_stage)
        return discard_stage

    def _barca_get_stage_discard(self):
        return self._barca_get_discard_stage()

    def _barca_is_stage_in_progress(self, stage=None):
        self.ensure_one()
        stage = stage or self.stage_id
        progress_stage = self._barca_get_progress_stage()
        return bool(progress_stage and stage == progress_stage)

    def _barca_is_stage_review(self, stage=None):
        self.ensure_one()
        stage = stage or self.stage_id
        review_stage = self._barca_get_review_stage()
        partial_close_stage = self._barca_get_close_partial_stage()
        return bool(review_stage and stage == review_stage)

    def _barca_is_stage_repaired(self, stage=None):
        return self._barca_is_stage_review(stage=stage)

    def _barca_is_stage_total_close(self, stage=None):
        self.ensure_one()
        stage = stage or self.stage_id
        close_stage = self._barca_get_close_total_stage()
        return bool(close_stage and stage == close_stage)

    def _barca_is_stage_partial_close(self, stage=None):
        self.ensure_one()
        stage = stage or self.stage_id
        close_stage = self._barca_get_close_partial_stage()
        return bool(close_stage and stage == close_stage)

    def _barca_is_stage_discard(self, stage=None):
        self.ensure_one()
        stage = stage or self.stage_id
        discard_stage = self._barca_get_discard_stage()
        return bool(discard_stage and stage == discard_stage)

    def _barca_is_stage_final_close(self, stage=None):
        self.ensure_one()
        stage = stage or self.stage_id
        return bool(
            stage
            and (
                self._barca_is_stage_total_close(stage)
                or self._barca_is_stage_partial_close(stage)
                or self._barca_is_stage_discard(stage)
            )
        )

    # -------------------------------------------------------------------------
    # Fase 5: Reserva de materiales
    # -------------------------------------------------------------------------

    barca_material_picking_id = fields.Many2one(
        "stock.picking",
        string="Reserva de materiales",
        readonly=True,
        copy=False,
        index=True,
    )

    barca_material_state = fields.Selection(
        [
            ("no_materials", "Sin materiales"),
            ("pending_reservation", "Pendiente reserva"),
            ("reserved", "Reservado"),
            ("partial", "Reserva parcial"),
            ("missing", "Sin stock suficiente"),
        ],
        string="Estado de materiales",
        default="pending_reservation",
        tracking=True,
        copy=False,
    )

    barca_pending_material = fields.Boolean(
        string="Pendiente de material",
        compute="_compute_barca_pending_material",
        store=True,
    )

    barca_material_picking_count = fields.Integer(
        string="Reservas de materiales",
        compute="_compute_barca_material_picking_count",
    )

    @api.depends("barca_material_state")
    def _compute_barca_pending_material(self):
        for rec in self:
            rec.barca_pending_material = rec.barca_material_state in (
                "partial",
                "missing",
            )

    @api.depends("barca_material_picking_id")
    def _compute_barca_material_picking_count(self):
        for rec in self:
            rec.barca_material_picking_count = 1 if rec.barca_material_picking_id else 0

    # -------------------------------------------------------------------------
    # Fase 5: Método principal de reserva
    # -------------------------------------------------------------------------

    def _barca_material_qty_to_reserve(self, material):
        return max(
            (material.requested_quantity or 0.0)
            - (material.reserved_quantity or 0.0)
            - (material.available_quantity or 0.0),
            0.0,
        )

    def action_barca_reserve_materials(self):
        """Crea una reserva de materiales (stock.picking) vinculada a la OT.

        - Agrupa materiales por producto/UdM.
        - Confirma y asigna el picking (no lo valida).
        - Actualiza reserved_quantity en las líneas de material.
        - Publica resumen en chatter.
        """
        self.ensure_one()

        # --- Limpiar vinculo si la ultima reserva fue cancelada o eliminada ---
        if self.barca_material_picking_id:
            picking = self.barca_material_picking_id
            if not picking.exists() or picking.state == "cancel":
                self.write({
                    "barca_material_picking_id": False,
                    "barca_material_state": "pending_reservation",
                })
                self.message_post(
                    body=(
                        "La reserva anterior (<b>%s</b>) estaba cancelada o fue eliminada. "
                        "Se ha limpiado el vinculo para permitir una nueva reserva."
                    ) % (picking.name if picking.exists() else "eliminada")
                )

        # --- Recolectar materiales válidos ---
        all_material_lines = self.env["barca.maintenance.workorder.line.material"]
        for activity in self.barca_activity_line_ids:
            for mat in activity.material_line_ids:
                if mat.product_id and self._barca_material_qty_to_reserve(mat) > 0:
                    if not mat.product_uom_id:
                        raise ValidationError(
                            "El material '%s' no tiene unidad de medida definida."
                            % mat.product_id.display_name
                        )
                    all_material_lines |= mat

        if not all_material_lines:
            if callable(getattr(self, "message_post", None)):
                self.message_post(
                    body="No hay diferencias pendientes por reservar en esta OT."
                )
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Sin materiales",
                    "message": "No hay diferencias pendientes por reservar.",
                    "type": "warning",
                    "sticky": False,
                },
            }

        # --- Determinar warehouse, ubicaciones y tipo de operación ---
        company = self.company_id or self.env.company

        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", company.id)], limit=1
        )
        if not warehouse:
            raise ValidationError(
                "No se encontró un almacén (warehouse) configurado para la compañía '%s'. "
                "Configure al menos un almacén antes de reservar materiales."
                % company.name
            )

        location_src = warehouse.lot_stock_id
        if not location_src:
            raise ValidationError(
                "El almacén '%s' no tiene configurada la ubicación de stock principal. "
                "Verifique la configuración del almacén." % warehouse.name
            )

        # Tipo de operación: preferir interna del warehouse, luego buscar cualquier interna
        picking_type = warehouse.int_type_id
        if not picking_type:
            picking_type = self.env["stock.picking.type"].search(
                [
                    ("code", "=", "internal"),
                    ("company_id", "=", company.id),
                    ("active", "=", True),
                ],
                limit=1,
            )
        if not picking_type:
            raise ValidationError(
                "No se encontró un tipo de operación interna para el almacén '%s'. "
                "Configure una operación de tipo 'Interno' antes de reservar materiales."
                % warehouse.name
            )

        # La bodega define el destino mediante el tipo de operación interna.
        location_dest = picking_type.default_location_dest_id
        if not location_dest or location_dest.id == location_src.id:
            raise ValidationError(
                "No se pudo determinar una ubicación destino para la reserva de mantenimiento. "
                "Configure una ubicación destino por defecto distinta de la ubicación de origen "
                "en el tipo de operación interna '%s' del almacén '%s'."
                % (picking_type.name, warehouse.name)
            )

        # --- Agrupar materiales por (product_id, product_uom_id) ---
        # Estructura: {(product_id, uom_id): qty_total}
        grouped_qty = defaultdict(float)
        for mat in all_material_lines:
            key = (mat.product_id.id, mat.product_uom_id.id)
            grouped_qty[key] += self._barca_material_qty_to_reserve(mat)

        # --- Crear stock.picking ---
        picking_vals = {
            "picking_type_id": picking_type.id,
            "location_id": location_src.id,
            "location_dest_id": location_dest.id,
            "origin": "OT %s" % (self.name or ""),
            "company_id": company.id,
            "scheduled_date": fields.Datetime.now(),
        }
        picking = self.env["stock.picking"].create(picking_vals)

        # --- Crear stock.move por cada grupo producto/UdM ---
        move_map = {}  # {(product_id, uom_id): stock.move}
        for (product_id, uom_id), qty in grouped_qty.items():
            product = self.env["product.product"].browse(product_id)
            uom = self.env["uom.uom"].browse(uom_id)
            move_vals = {
                "name": product.display_name,
                "product_id": product_id,
                "product_uom_qty": qty,
                "product_uom": uom_id,
                "location_id": location_src.id,
                "location_dest_id": location_dest.id,
                "picking_id": picking.id,
                "company_id": company.id,
            }
            move = self.env["stock.move"].create(move_vals)
            move_map[(product_id, uom_id)] = move

        # --- Confirmar y asignar (NO validar) ---
        picking.action_confirm()
        picking.action_assign()

        # --- Calcular cantidades reservadas por movimiento ---
        # En Odoo 18, stock.move tiene reserved_availability (float) o
        # quantity_done, pero la cantidad realmente reservada se lee desde
        # move_line_ids sumando reserved_qty o qty (según versión).
        # Usamos el campo estándar 'reserved_availability' disponible en Odoo 16+
        # y confirmado en Odoo 18 como la cantidad reservada del movimiento.
        def _get_move_reserved(move):
            """Retorna la cantidad reservada en el movimiento de forma segura."""
            if hasattr(move, "reserved_availability"):
                return move.reserved_availability
            # Fallback: sumar desde move_line_ids
            reserved = 0.0
            for ml in move.move_line_ids:
                qty_field = "quantity" if hasattr(ml, "quantity") else "reserved_qty"
                reserved += getattr(ml, qty_field, 0.0)
            return reserved

        reserved_by_key = {}
        total_requested = 0.0
        total_reserved = 0.0
        for (product_id, uom_id), move in move_map.items():
            move.invalidate_recordset()
            requested = grouped_qty[(product_id, uom_id)]
            reserved = _get_move_reserved(move)
            reserved_by_key[(product_id, uom_id)] = reserved
            total_requested += requested
            total_reserved += reserved

        # --- Determinar estado final ---
        if total_requested <= 0:
            final_state = "no_materials"
        elif total_reserved >= total_requested:
            final_state = "reserved"
        elif total_reserved > 0:
            final_state = "partial"
        else:
            final_state = "missing"

        # --- Distribuir reserved_quantity entre líneas de material (secuencial) ---
        # Agrupamos las líneas originales por (product_id, uom_id) en orden
        lines_by_key = defaultdict(list)
        for activity in self.barca_activity_line_ids:
            for mat in activity.material_line_ids:
                if mat.product_id and self._barca_material_qty_to_reserve(mat) > 0 and mat.product_uom_id:
                    key = (mat.product_id.id, mat.product_uom_id.id)
                    lines_by_key[key].append(mat)

        for key, lines in lines_by_key.items():
            available = reserved_by_key.get(key, 0.0)
            for mat in lines:
                pending_qty = self._barca_material_qty_to_reserve(mat)
                assignable = min(pending_qty, available)
                assignable = max(assignable, 0.0)
                mat.write({"reserved_quantity": (mat.reserved_quantity or 0.0) + assignable})
                available -= assignable
                if available <= 0:
                    available = 0.0

        # --- Guardar en la OT ---
        self.write(
            {
                "barca_material_picking_id": picking.id,
                "barca_material_state": final_state,
            }
        )

        # --- Publicar resumen en chatter ---
        state_labels = {
            "reserved": "✅ Reservado completo",
            "partial": "⚠️ Reserva parcial",
            "missing": "❌ Sin stock suficiente",
            "no_materials": "Sin materiales",
        }
        body = (
            "<b>Reserva de materiales creada</b><br/>"
            "Picking: <b>%s</b><br/>"
            "Productos/movimientos: <b>%s</b><br/>"
            "Cantidad total solicitada: <b>%.2f</b><br/>"
            "Cantidad total reservada: <b>%.2f</b><br/>"
            "Estado: <b>%s</b>"
        ) % (
            picking.name,
            len(move_map),
            total_requested,
            total_reserved,
            state_labels.get(final_state, final_state),
        )
        if callable(getattr(self, "message_post", None)):
            self.message_post(body=body)

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Reserva creada",
                "message": "Picking %s creado. Estado: %s"
                % (picking.name, state_labels.get(final_state, final_state)),
                "type": "success" if final_state == "reserved" else "warning",
                "sticky": False,
            },
        }

    def action_barca_open_material_picking(self):
        """Abre el picking de reserva de materiales vinculado a la OT."""
        self.ensure_one()
        if not self.barca_material_picking_id:
            raise ValidationError(
                "Esta OT no tiene una reserva de materiales vinculada."
            )
        return {
            "type": "ir.actions.act_window",
            "name": "Reserva de materiales",
            "res_model": "stock.picking",
            "res_id": self.barca_material_picking_id.id,
            "view_mode": "form",
            "target": "current",
        }

    # -------------------------------------------------------------------------
    # Fase 6: Entrega, consumo y cierre de materiales
    # -------------------------------------------------------------------------

    barca_material_withdrawn = fields.Boolean(
        string="Materiales entregados",
        default=False,
        readonly=True,
        copy=False,
        tracking=True,
    )

    barca_material_delivery_date = fields.Datetime(
        string="Fecha entrega materiales",
        readonly=True,
        copy=False,
    )

    barca_material_delivered_by_id = fields.Many2one(
        "res.users",
        string="Entregado por",
        readonly=True,
        copy=False,
    )

    barca_material_closed = fields.Boolean(
        string="Ciclo de materiales cerrado",
        default=False,
        readonly=True,
        copy=False,
        tracking=True,
    )

    barca_material_closed_date = fields.Datetime(
        string="Fecha cierre materiales",
        readonly=True,
        copy=False,
    )

    barca_material_closed_by_id = fields.Many2one(
        "res.users",
        string="Cerrado por",
        readonly=True,
        copy=False,
    )

    barca_material_note = fields.Text(
        string="Observación de materiales",
    )

    barca_currency_id = fields.Many2one(
        "res.currency",
        string="Moneda",
        related="company_id.currency_id",
        readonly=True,
        store=True,
    )

    barca_estimated_material_cost = fields.Monetary(
        string="Costo estimado materiales",
        compute="_compute_barca_material_costs",
        currency_field="barca_currency_id",
        store=True,
    )

    barca_real_material_cost = fields.Monetary(
        string="Costo real materiales",
        compute="_compute_barca_material_costs",
        currency_field="barca_currency_id",
        store=True,
    )

    @api.depends(
        "barca_activity_line_ids.material_line_ids.estimated_quantity",
        "barca_activity_line_ids.material_line_ids.consumed_quantity",
        "barca_activity_line_ids.material_line_ids.product_id.standard_price",
    )
    def _compute_barca_material_costs(self):
        for rec in self:
            estimated = 0.0
            real = 0.0
            for line in rec._barca_get_material_lines():
                price = line.product_id.standard_price or 0.0
                estimated += (line.estimated_quantity or 0.0) * price
                real += (line.consumed_quantity or 0.0) * price
            rec.barca_estimated_material_cost = estimated
            rec.barca_real_material_cost = real

    # -------------------------------------------------------------------------
    # Fase 6: Métodos principales
    # -------------------------------------------------------------------------

    def _barca_get_material_lines(self):
        """Retorna todas las lineas de material de la OT que tienen product_id.

        Nota: no lleva ensure_one() porque es llamado desde _compute_barca_material_costs
        dentro de un for rec in self. La garantia de singleton la dan los callers.
        """
        lines = self.env["barca.maintenance.workorder.line.material"]
        for activity in self.barca_activity_line_ids:
            for mat in activity.material_line_ids:
                if mat.product_id:
                    lines |= mat
        return lines

    def _barca_get_move_done_quantity(self, move):
        """Retorna la cantidad hecha de un movimiento validado."""
        done_qty = 0.0
        for move_line in move.move_line_ids:
            if hasattr(move_line, "quantity"):
                done_qty += move_line.quantity or 0.0
            elif hasattr(move_line, "qty_done"):
                done_qty += move_line.qty_done or 0.0
        if done_qty:
            return done_qty

        for field_name in ("quantity_done", "quantity"):
            if hasattr(move, field_name):
                return getattr(move, field_name) or 0.0
        return 0.0

    def _barca_get_material_pickings(self):
        self.ensure_one()
        pickings = self.env["stock.picking"]
        if self.barca_material_picking_id:
            pickings |= self.barca_material_picking_id
        if self.name:
            pickings |= self.env["stock.picking"].search(
                [("origin", "=", "OT %s" % self.name)]
            )
        return pickings

    def _barca_sync_available_quantities_from_picking(self, material_lines=None):
        """Sincroniza disponible Serviteca desde el traslado validado en Inventario."""
        self.ensure_one()
        pickings = self._barca_get_material_pickings()
        if not pickings:
            raise ValidationError(
                "Debe crear una reserva de materiales y validar el traslado interno "
                "en Inventario antes de cerrar el ciclo de materiales."
            )
        pending_pickings = pickings.filtered(
            lambda picking: picking.state not in ("done", "cancel")
        )
        if pending_pickings:
            state_label = dict(pending_pickings[0]._fields["state"].selection).get(
                pending_pickings[0].state, pending_pickings[0].state
            )
            raise ValidationError(
                "La entrega de materiales debe realizarse desde Inventario validando "
                "el traslado interno '%s'. Estado actual: %s."
                % (pending_pickings[0].name, state_label)
            )

        material_lines = material_lines or self._barca_get_material_lines()
        done_by_key = defaultdict(float)
        for picking in pickings.filtered(lambda item: item.state == "done"):
            picking_moves = (
                picking.move_ids
                if "move_ids" in picking._fields
                else picking.move_ids_without_package
            )
            for move in picking_moves.filtered(lambda m: m.state != "cancel"):
                if move.product_id and move.product_uom:
                    key = (move.product_id.id, move.product_uom.id)
                    done_by_key[key] += self._barca_get_move_done_quantity(move)

        total_withdrawn = 0.0
        lines_by_key = defaultdict(list)
        for mat in material_lines:
            if mat.product_id and mat.product_uom_id:
                key = (mat.product_id.id, mat.product_uom_id.id)
                lines_by_key[key].append(mat)

        for key, lines in lines_by_key.items():
            available = done_by_key.get(key, 0.0)
            for mat in lines:
                transferred = min(mat.requested_quantity or 0.0, available)
                transferred = max(transferred, 0.0)
                already_synced = mat.withdrawn_quantity or 0.0
                delta = max(transferred - already_synced, 0.0)
                if delta:
                    mat.write(
                        {
                            "available_quantity": (mat.available_quantity or 0.0)
                            + delta,
                            "reserved_quantity": max(
                                (mat.reserved_quantity or 0.0) - delta, 0.0
                            ),
                            "withdrawn_quantity": transferred,
                        }
                    )
                total_withdrawn += transferred
                available -= transferred
                if available <= 0:
                    available = 0.0

        if total_withdrawn <= 0:
            raise ValidationError(
                "El traslado interno '%s' esta validado, pero no registra cantidades "
                "entregadas para los materiales de esta OT." % picking.name
            )

        self.write(
            {
                "barca_material_withdrawn": True,
                "barca_material_delivery_date": picking.date_done or fields.Datetime.now(),
                "barca_material_delivered_by_id": picking.write_uid.id or self.env.user.id,
            }
        )
        return total_withdrawn

    def _barca_sync_withdrawn_quantities_from_picking(self, material_lines=None):
        """Compatibilidad: usar disponible Serviteca como cantidad retirada."""
        return self._barca_sync_available_quantities_from_picking(material_lines)

    def action_barca_deliver_materials(self):
        """Compatibilidad: la entrega se registra validando el picking en Inventario."""
        raise ValidationError(
            "La entrega de materiales debe realizarse desde Inventario, validando "
            "el traslado interno de la reserva. La OT solo solicita/reserva "
            "materiales y luego sincroniza las cantidades retiradas al cerrar "
            "el ciclo de materiales."
        )

    def action_barca_close_materials(self):
        """Cierra el ciclo de materiales: calcula sobrantes y registra cierre.

        - Valida que se hayan entregado materiales.
        - Valida que consumo <= cantidad entregada por línea.
        - Calcula returned_quantity = withdrawn_quantity - consumed_quantity.
        - Registra fecha y usuario de cierre.
        - Publica resumen en chatter.
        """
        self.ensure_one()

        material_lines = self._barca_get_material_lines()
        if not material_lines:
            raise ValidationError(
                "No hay materiales asociados a las actividades de esta OT."
            )

        if self.barca_material_closed:
            raise ValidationError(
                "El ciclo de materiales de esta OT ya está cerrado."
            )

        if any(line.requested_quantity > 0 for line in material_lines):
            self._barca_sync_available_quantities_from_picking(material_lines)
        elif not self.barca_material_withdrawn:
            self.write(
                {
                    "barca_material_withdrawn": True,
                    "barca_material_delivery_date": fields.Datetime.now(),
                    "barca_material_delivered_by_id": self.env.user.id,
                }
            )

        # Validaciones de cantidades y cálculo de sobrante
        for mat in material_lines:
            product_name = mat.product_id.display_name or "desconocido"
            for field_name, label in (
                ("estimated_quantity", "estimada"),
                ("requested_quantity", "a solicitar"),
                ("available_quantity", "disponible Serviteca"),
                ("reserved_quantity", "reservada"),
                ("withdrawn_quantity", "entregada"),
                ("consumed_quantity", "consumida"),
                ("returned_quantity", "devuelta"),
            ):
                if (mat[field_name] or 0.0) < 0:
                    raise ValidationError(
                        "La cantidad %s del producto '%s' no puede ser negativa."
                        % (label, product_name)
                    )

            consumed = mat.consumed_quantity or 0.0
            available = mat.available_quantity or 0.0
            if consumed > available:
                raise ValidationError(
                    "El consumo real del producto '%s' (%.2f) no puede ser mayor "
                    "que la cantidad disponible en Serviteca (%.2f)."
                    % (product_name, consumed, available)
                )

        # Calcular sobrante, escribir y acumular costos en el mismo loop
        total_withdrawn = 0.0
        total_consumed = 0.0
        total_returned = 0.0
        estimated_cost = 0.0
        real_cost = 0.0

        for mat in material_lines:
            consumed = mat.consumed_quantity or 0.0
            available = mat.available_quantity or 0.0
            returned = available - consumed
            returned = max(returned, 0.0)
            mat.write({"returned_quantity": returned})
            total_withdrawn += available
            total_consumed += consumed
            total_returned += returned
            price = mat.product_id.standard_price or 0.0
            estimated_cost += (mat.estimated_quantity or 0.0) * price
            real_cost += consumed * price

        diff_cost = estimated_cost - real_cost

        self.write(
            {
                "barca_material_closed": True,
                "barca_material_closed_date": fields.Datetime.now(),
                "barca_material_closed_by_id": self.env.user.id,
            }
        )
        # Los campos store=True se recalculan automáticamente porque
        # consumed_quantity (dependencia del compute) fue modificado antes.
        # No se llama _compute_barca_material_costs() manualmente.

        body = (
            "<b>Ciclo de materiales cerrado</b><br/>"
            "Total entregado: <b>%.2f</b><br/>"
            "Total consumido: <b>%.2f</b><br/>"
            "Total devuelto/sobrante: <b>%.2f</b><br/>"
            "Costo estimado: <b>%.2f</b><br/>"
            "Costo real: <b>%.2f</b><br/>"
            "Diferencia (estimado - real): <b>%.2f</b>"
        ) % (
            total_withdrawn,
            total_consumed,
            total_returned,
            estimated_cost,
            real_cost,
            diff_cost,
        )
        self.message_post(body=body)

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Ciclo de materiales cerrado",
                "message": "Consumido: %.2f | Devuelto: %.2f | Costo real: %.2f"
                % (total_consumed, total_returned, real_cost),
                "type": "success",
                "sticky": False,
            },
        }

    # -------------------------------------------------------------------------
    # Campos existentes (Fases 1-4)
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # Módulo 3: flujo de revisión
    # -------------------------------------------------------------------------

    _BARCA_EXECUTOR_PROTECTED_FIELDS = {
        "name",
        "request_date",
        "schedule_date",
        "barca_start_datetime",
    }

    barca_state = fields.Selection(
        [
            ("in_progress", "En ejecución"),
            ("under_review", "En revisión"),
            ("approved", "Aprobada"),
        ],
        string="Estado Barca legado",
        default="in_progress",
        tracking=True,
        copy=False,
        help="Campo histórico. El flujo vigente de OT usa stage_id.",
    )

    barca_locked_for_executor = fields.Boolean(
        string="Bloqueada para ejecutor",
        compute="_compute_barca_locked_for_executor",
    )
    barca_stage_is_in_progress = fields.Boolean(
        string="Etapa En progreso",
        compute="_compute_barca_stage_flags",
    )
    barca_stage_is_review = fields.Boolean(
        string="Etapa En revisión",
        compute="_compute_barca_stage_flags",
    )
    barca_stage_is_partial_close = fields.Boolean(
        string="Etapa Cierre Parcial",
        compute="_compute_barca_stage_flags",
    )
    barca_stage_is_total_close = fields.Boolean(
        string="Etapa Cierre Total",
        compute="_compute_barca_stage_flags",
    )
    barca_stage_is_discard = fields.Boolean(
        string="Etapa Desechar",
        compute="_compute_barca_stage_flags",
    )
    barca_stage_is_repaired = fields.Boolean(
        string="Etapa En revisión",
        compute="_compute_barca_stage_flags",
    )

    barca_reviewer_id = fields.Many2one(
        "res.users",
        string="Programador revisor",
        tracking=True,
        domain="['|', ('groups_id.name', 'like', 'Barca / Programador'), "
               "('groups_id.name', 'like', 'Barca / Administrador')]",
        help="Programador que recibirá la OT para revisión final.",
    )

    barca_return_reason = fields.Text(
        string="Motivo de devolución",
        copy=False,
        help="Comentario del programador al devolver la OT a ejecución.",
    )

    barca_return_count = fields.Integer(
        string="N° devoluciones",
        default=0,
        copy=False,
        readonly=True,
    )

    barca_alert_id = fields.Many2one(
        "barca.maintenance.alert",
        string="Aviso Barca",
        index=True,
    )
    barca_start_datetime = fields.Datetime(
        string="Fecha y hora de inicio",
        copy=False,
        readonly=True,
        tracking=True,
        help="Primer inicio real de la OT. Se registra al iniciar la primera "
             "actividad y no se modifica durante el ciclo de vida.",
    )
    barca_activity_line_ids = fields.One2many(
        "barca.maintenance.workorder.line",
        "maintenance_request_id",
        string="Actividades",
    )
    barca_activity_count = fields.Integer(
        string="N° actividades Barca",
        compute="_compute_barca_activity_counts",
    )
    barca_total_activity_count = fields.Integer(
        string="Total actividades",
        compute="_compute_barca_activity_counts",
    )
    barca_notified_activity_count = fields.Integer(
        string="Actividades notificadas",
        compute="_compute_barca_activity_counts",
    )
    barca_closed_activity_count = fields.Integer(
        string="Actividades cerradas",
        compute="_compute_barca_activity_counts",
    )
    barca_all_activities_notified = fields.Boolean(
        string="Todas las actividades notificadas",
        compute="_compute_barca_activity_counts",
    )
    barca_all_activities_closed = fields.Boolean(
        string="Todas las actividades cerradas",
        compute="_compute_barca_activity_counts",
    )

    @api.depends("barca_activity_line_ids", "barca_activity_line_ids.state")
    def _compute_barca_activity_counts(self):
        for request in self:
            total = len(request.barca_activity_line_ids)
            notified = len(
                request.barca_activity_line_ids.filtered(
                    lambda line: line.state == "notified"
                )
            )

            request.barca_activity_count = total
            request.barca_total_activity_count = total
            request.barca_notified_activity_count = notified
            request.barca_closed_activity_count = 0
            request.barca_all_activities_notified = total > 0 and notified == total
            request.barca_all_activities_closed = False

    def _barca_is_restricted_executor(self):
        user = self.env.user
        return (
            user.has_group("zmm_ajustes.group_barca_ejecutor")
            and not user.has_group("zmm_ajustes.group_barca_programador")
            and not user.has_group("zmm_ajustes.group_barca_admin")
        )

    @api.depends("stage_id")
    def _compute_barca_stage_flags(self):
        progress_stage = self._barca_get_progress_stage()
        review_stage = self._barca_get_review_stage()
        partial_close_stage = self._barca_get_close_partial_stage()
        total_close_stage = self._barca_get_close_total_stage()
        discard_stage = self._barca_get_discard_stage()
        for request in self:
            request.barca_stage_is_in_progress = bool(
                progress_stage and request.stage_id == progress_stage
            )
            request.barca_stage_is_review = bool(
                review_stage and request.stage_id == review_stage
            )
            request.barca_stage_is_repaired = bool(
                review_stage and request.stage_id == review_stage
            )
            request.barca_stage_is_partial_close = bool(
                partial_close_stage and request.stage_id == partial_close_stage
            )
            request.barca_stage_is_total_close = bool(
                total_close_stage and request.stage_id == total_close_stage
            )
            request.barca_stage_is_discard = bool(
                discard_stage and request.stage_id == discard_stage
            )

    @api.depends("stage_id")
    @api.depends_context("uid")
    def _compute_barca_locked_for_executor(self):
        restricted_executor = self._barca_is_restricted_executor()
        for request in self:
            request.barca_locked_for_executor = (
                restricted_executor and not request._barca_is_stage_in_progress()
            )

    def _barca_check_executor_write_access(self, vals):
        if not self._barca_is_restricted_executor():
            return

        protected_fields = self._BARCA_EXECUTOR_PROTECTED_FIELDS & set(vals)
        if protected_fields:
            labels = [
                self._fields[field_name].string
                for field_name in sorted(protected_fields)
                if field_name in self._fields
            ]
            raise ValidationError(
                "El ejecutor no puede modificar estos campos de la OT: %s."
                % ", ".join(labels)
            )

        if (
            "stage_id" in vals
            and not self.env.context.get("allow_barca_executor_stage_write")
        ):
            raise ValidationError(
                "El ejecutor no puede cambiar manualmente la etapa de revision "
                "de la OT. Use las acciones disponibles."
            )

        blocked_requests = self.filtered(
            lambda request: not request._barca_is_stage_in_progress()
        )
        if blocked_requests:
            raise ValidationError(
                "El ejecutor solo puede editar una OT cuando esta en estado "
                "En progreso. Si la OT esta en revision o cerrada, debe "
                "esperar la devolucion del programador."
            )

    def _barca_is_barca_flow_request(self):
        self.ensure_one()
        return bool(self.barca_alert_id or self.barca_activity_line_ids)

    def _barca_check_can_send_to_review(self):
        self.ensure_one()
        if not self._barca_is_stage_in_progress():
            raise ValidationError(
                "Solo se puede enviar a revisión una OT en etapa En progreso."
            )
        if not self.barca_activity_line_ids:
            raise ValidationError(
                "La OT debe tener al menos una actividad para enviarse a revisión."
            )
        pending_lines = self.barca_activity_line_ids.filtered(
            lambda line: line.state != "notified"
        )
        if pending_lines:
            raise ValidationError(
                "Todas las actividades deben estar notificadas antes de enviar "
                "la OT a revisión. Actividades pendientes: %s."
                % ", ".join(l.activity_id.name or str(l.id) for l in pending_lines)
            )

    def _barca_has_pending_materials(self):
        self.ensure_one()
        material_lines = self._barca_get_material_lines()
        if not material_lines:
            return False
        if self.barca_material_closed:
            return False

        for line in material_lines:
            requested = line.requested_quantity or 0.0
            reserved = line.reserved_quantity or 0.0
            available = line.available_quantity or 0.0
            consumed = line.consumed_quantity or 0.0

            pending_request = max(requested - reserved - available, 0.0)
            if pending_request > 0:
                return True
            if reserved > 0:
                return True
            if consumed > available:
                return True
            if available and consumed < available and not line.returned_quantity:
                return True

        return False

    def _barca_check_no_pending_materials_for_total_close(self):
        self.ensure_one()
        if self._barca_has_pending_materials():
            raise ValidationError(
                "No se puede realizar cierre total porque existen materiales "
                "pendientes de entrega, consumo, devolución o cierre. Puede "
                "realizar un cierre parcial o regularizar los materiales."
            )

    def _barca_check_can_close_total(self):
        self.ensure_one()
        if not self._barca_is_stage_review():
            raise ValidationError(
                "Solo se puede realizar cierre total desde la etapa En revisión."
            )
        self._barca_check_no_pending_materials_for_total_close()

    def _barca_check_can_close_partial(self):
        self.ensure_one()
        if not self._barca_is_stage_review():
            raise ValidationError(
                "Solo se puede realizar cierre parcial desde la etapa En revisión."
            )

    def _barca_check_can_return_to_progress(self):
        self.ensure_one()
        if not self._barca_is_stage_review():
            raise ValidationError(
                "Solo se puede devolver a progreso una OT que este en etapa "
                "En revision."
            )

    def _barca_check_can_discard(self):
        self.ensure_one()
        if self._barca_is_restricted_executor():
            raise ValidationError("El ejecutor no puede desechar una OT.")
        if not self._barca_is_stage_review():
            raise ValidationError(
                "Solo se puede desechar una OT Barca desde la etapa En revisión."
            )

    def _barca_is_allowed_stage(self, stage):
        self.ensure_one()
        return bool(
            stage
            and (
                self._barca_is_stage_in_progress(stage)
                or self._barca_is_stage_review(stage)
                or self._barca_is_stage_total_close(stage)
                or self._barca_is_stage_partial_close(stage)
                or self._barca_is_stage_discard(stage)
            )
        )

    def _barca_get_allowed_stage_names(self):
        stage_names = []
        for stage in (
            self._barca_get_progress_stage(),
            self._barca_get_review_stage(),
            self._barca_get_close_partial_stage(),
            self._barca_get_close_total_stage(),
            self._barca_get_discard_stage(),
        ):
            if stage and stage.name not in stage_names:
                stage_names.append(stage.name)
        return ", ".join(stage_names) or (
            "En progreso, En revisión, Cierre Parcial, Cierre Total, Desechar"
        )

    def _barca_check_stage_transition(self, target_stage):
        if not target_stage:
            return
        for request in self:
            if not request._barca_is_barca_flow_request():
                continue
            if request.stage_id == target_stage:
                continue
            if not request._barca_is_allowed_stage(target_stage):
                raise ValidationError(
                    "La etapa '%s' no pertenece al flujo Barca de OT. "
                    "Use una de estas etapas: %s."
                    % (
                        target_stage.name,
                        request._barca_get_allowed_stage_names(),
                    )
                )
            if request._barca_is_stage_in_progress(target_stage):
                request._barca_check_can_return_to_progress()
            elif request._barca_is_stage_review(target_stage):
                request._barca_check_can_send_to_review()
            elif request._barca_is_stage_total_close(target_stage):
                request._barca_check_can_close_total()
            elif request._barca_is_stage_partial_close(target_stage):
                request._barca_check_can_close_partial()
            elif request._barca_is_stage_discard(target_stage):
                request._barca_check_can_discard()

    def _barca_close_linked_alert_if_needed(self):
        for request in self:
            if (
                request.barca_alert_id
                and request.barca_alert_id.state != "closed"
                and request._barca_is_stage_final_close()
            ):
                request.barca_alert_id.action_close()

    def _barca_notification_action(self, title, message, notification_type="success"):
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": title,
                "message": message,
                "type": notification_type,
                "sticky": False,
                "next": {
                    "type": "ir.actions.client",
                    "tag": "reload",
                },
            },
        }

    def write(self, vals):
        if "barca_start_datetime" in vals:
            if not self.env.context.get("allow_barca_workorder_start_write"):
                raise ValidationError(
                    "La fecha y hora de inicio de la OT no se puede modificar "
                    "manualmente."
                )
            for request in self:
                if request.barca_start_datetime:
                    raise ValidationError(
                        "La fecha y hora de inicio de la OT ya fue registrada "
                        "y no puede modificarse."
                    )

        self._barca_check_executor_write_access(vals)
        target_stage = False
        if "stage_id" in vals and vals["stage_id"]:
            target_stage = self.env["maintenance.stage"].browse(vals["stage_id"])
            if not self.env.context.get("skip_barca_stage_transition"):
                self._barca_check_stage_transition(target_stage)
        result = super().write(vals)
        if target_stage and not self.env.context.get("skip_barca_stage_transition"):
            self._barca_close_linked_alert_if_needed()
        return result

    def action_barca_send_to_review(self):
        """Envía la OT a revisión del programador."""
        self.ensure_one()
        self._barca_check_can_send_to_review()

        review_stage = self._barca_get_review_stage()
        if not review_stage:
            raise ValidationError(
                "No se encontró la etapa En revisión para enviar la OT a revisión."
            )

        reviewer = (
            self.barca_alert_id.approved_by_id
            if self.barca_alert_id and self.barca_alert_id.approved_by_id
            else self.create_uid
        )
        self.with_context(allow_barca_executor_stage_write=True).write(
            {
                "stage_id": review_stage.id,
                "barca_reviewer_id": reviewer.id,
            }
        )

        self.message_post(
            body=(
                "<b>OT enviada a revisión</b><br/>"
                "Enviada por: <b>%s</b><br/>"
                "Revisor: <b>%s</b>"
            ) % (self.env.user.name, reviewer.name),
            partner_ids=reviewer.partner_id.ids,
        )
        return self._barca_notification_action(
            "OT enviada a revisión",
            "Se notificó a %s." % reviewer.name,
        )

    def _barca_close_from_review(self, close_stage, close_label):
        self.ensure_one()
        if not self._barca_is_stage_repaired():
            raise ValidationError(
                "Solo se puede cerrar una OT que esté en etapa En revisión."
            )
        if not close_stage:
            raise ValidationError("No se encontró la etapa %s." % close_label)

        self.write({"stage_id": close_stage.id})
        self.barca_activity_line_ids.filtered(
            lambda l: l.barca_added_after_return
        ).write({"barca_added_after_return": False})

        responsible = self.user_id
        partner_ids = responsible.partner_id.ids if responsible else []
        self.message_post(
            body=(
                "<b>OT cerrada: %s</b><br/>"
                "Cerrada por: <b>%s</b>"
            ) % (close_label, self.env.user.name),
            partner_ids=partner_ids,
        )
        return self._barca_notification_action(
            close_label,
            "La OT quedó en %s." % close_label,
        )

    def action_barca_close_total(self):
        """Cierra totalmente la OT desde la etapa En revisión."""
        return self._barca_close_from_review(
            self._barca_get_close_total_stage(),
            "Cierre Total",
        )

    def action_barca_close_partial(self):
        """Cierra parcialmente la OT desde la etapa En revisión."""
        return self._barca_close_from_review(
            self._barca_get_close_partial_stage(),
            "Cierre Parcial",
        )

    def action_barca_discard(self):
        """Desecha una OT Barca desde la etapa En revision."""
        self.ensure_one()
        self._barca_check_can_discard()

        discard_stage = self._barca_get_discard_stage()
        if not discard_stage:
            raise ValidationError("No se encontro la etapa Desechar.")

        self.write({"stage_id": discard_stage.id})
        self.message_post(
            body=(
                "<b>OT desechada</b><br/>"
                "Desechada por: <b>%s</b>"
            ) % self.env.user.name,
        )
        return self._barca_notification_action(
            "OT desechada",
            "La OT quedo en etapa Desechar.",
            notification_type="warning",
        )

    def action_barca_approve(self):
        """Compatibilidad: la antigua aprobación equivale a Cierre Total."""
        return self.action_barca_close_total()

    def action_barca_return_to_progress(self):
        """Devuelve la OT a ejecución. Solo programador y admin."""
        self.ensure_one()

        if not self._barca_is_stage_repaired():
            raise ValidationError(
                "Solo se puede devolver una OT que esté en etapa En revisión."
            )
        if not self.barca_return_reason or not self.barca_return_reason.strip():
            raise ValidationError(
                "Debe ingresar el motivo de devolución antes de devolver la OT."
            )

        progress_stage = self._barca_get_progress_stage()
        if not progress_stage:
            raise ValidationError(
                "No se encontró la etapa En progreso para devolver la OT."
            )

        self.write({
            "stage_id": progress_stage.id,
            "barca_return_count": self.barca_return_count + 1,
        })
        if self.barca_alert_id and self.barca_alert_id.state == "closed":
            self.barca_alert_id.write(
                {
                    "state": "in_progress",
                    "closed_by_id": False,
                    "close_date": False,
                }
            )

        responsible = self.user_id
        partner_ids = responsible.partner_id.ids if responsible else []
        self.message_post(
            body=(
                "<b>OT devuelta a ejecución</b><br/>"
                "Devuelta por: <b>%s</b><br/>"
                "Motivo: %s"
            ) % (self.env.user.name, self.barca_return_reason),
            partner_ids=partner_ids,
        )
        return self._barca_notification_action(
            "OT devuelta a ejecución",
            "Se notificó a %s." % (responsible.name if responsible else "nadie"),
            notification_type="warning",
        )


    def action_barca_reopen_partial_to_review(self):
        """Reabre una OT con cierre parcial o total y la devuelve a revision."""
        self.ensure_one()
        if not (
            self._barca_is_stage_partial_close()
            or self._barca_is_stage_total_close()
            or self._barca_is_stage_discard()
        ):
            raise ValidationError(
                "Solo se puede reabrir a revision una OT en Cierre Parcial "
                "Cierre Total o Desechar."
            )

        review_stage = self._barca_get_review_stage()
        if not review_stage:
            raise ValidationError("No se encontro la etapa En revision.")

        self.with_context(skip_barca_stage_transition=True).write(
            {"stage_id": review_stage.id}
        )
        if self.barca_alert_id and self.barca_alert_id.state == "closed":
            self.barca_alert_id.with_context(allow_alert_state_write=True).write(
                {
                    "state": "in_progress",
                    "closed_by_id": False,
                    "close_date": False,
                }
            )
        self.message_post(
            body=(
                "<b>OT reabierta a revision</b><br/>"
                "Reabierta por: <b>%s</b>"
            ) % self.env.user.name
        )
        return self._barca_notification_action(
            "OT reabierta",
            "La OT volvio a En revision.",
            notification_type="warning",
        )

    def reset_equipment_request(self):
        """Reabre una OT archivada sin sacarla del flujo Barca."""
        barca_requests = self.filtered(lambda request: request._barca_is_barca_flow_request())
        other_requests = self - barca_requests

        result = True
        if other_requests:
            result = super(MaintenanceRequest, other_requests).reset_equipment_request()

        if barca_requests:
            barca_requests.write({"archive": False})
            for request in barca_requests:
                request.message_post(
                    body=(
                        "<b>OT reabierta</b><br/>"
                        "Reabierta por: <b>%s</b><br/>"
                        "Etapa conservada: <b>%s</b>"
                    )
                    % (self.env.user.name, request.stage_id.name or "")
                )
        return result

class StockPicking(models.Model):
    _inherit = "stock.picking"

    def _barca_sync_linked_maintenance_requests(self):
        done_pickings = self.filtered(lambda picking: picking.state == "done")
        if not done_pickings:
            return
        requests = self.env["maintenance.request"].search(
            [("barca_material_picking_id", "in", done_pickings.ids)]
        )
        origins = done_pickings.mapped("origin")
        request_names = [
            origin[3:]
            for origin in origins
            if isinstance(origin, str) and origin.startswith("OT ")
        ]
        if request_names:
            requests |= self.env["maintenance.request"].search(
                [("name", "in", request_names)]
            )
        for request in requests:
            request._barca_sync_available_quantities_from_picking()

    def button_validate(self):
        result = super().button_validate()
        self._barca_sync_linked_maintenance_requests()
        return result

    def write(self, vals):
        result = super().write(vals)
        if vals.get("state") == "done":
            self._barca_sync_linked_maintenance_requests()
        return result


class BarcaMaintenanceWorkorderLine(models.Model):
    _name = "barca.maintenance.workorder.line"
    _description = "Actividad de orden de trabajo Barca"
    _order = "sequence, id"

    sequence = fields.Integer(string="Secuencia", default=10)

    barca_added_after_return = fields.Boolean(
        string="Agregada tras devolución",
        default=False,
        copy=False,
        help="Marcada True cuando el programador agrega o modifica esta actividad "
             "después de una devolución. Se limpia al aprobar la OT.",
    )

    maintenance_request_id = fields.Many2one(
        "maintenance.request",
        string="Orden de Trabajo",
        required=True,
        ondelete="cascade",
        index=True,
    )

    alert_line_id = fields.Many2one(
        "barca.maintenance.alert.line",
        string="Actividad del aviso origen",
        ondelete="set null",
    )

    alert_id = fields.Many2one(
        "barca.maintenance.alert",
        string="Aviso",
        related="alert_line_id.alert_id",
        store=True,
        readonly=True,
    )

    plan_line_id = fields.Many2one(
        "barca.maintenance.plan.line",
        string="Línea de plan origen",
        related="alert_line_id.plan_line_id",
        store=True,
        readonly=True,
    )

    technical_location_id = fields.Many2one(
        "barca.technical.location",
        string="Ubicación técnica",
        required=True,
    )

    intervention_type_id = fields.Many2one(
        "barca.intervention.type",
        string="Tipo de intervención",
    )

    activity_id = fields.Many2one(
        "barca.maintenance.activity",
        string="Actividad",
        required=True,
    )

    description = fields.Text(string="Descripción")

    estimated_duration = fields.Float(
        string="Duración estimada (hrs)",
        digits=(6, 2),
    )

    state = fields.Selection(
        [
            ("pending", "Pendiente"),
            ("in_progress", "En ejecución"),
            ("notified", "Notificada"),
        ],
        string="Estado operativo",
        default="pending",
        required=True,
    )

    note = fields.Text(string="Observaciones")

    notification_note = fields.Text(
        string="Descripción de lo realizado",
    )

    result = fields.Selection(
        [
            ("resolved", "Resuelto"),
            ("partial", "Parcial"),
            ("not_resolved", "No resuelto"),
        ],
        string="Resultado",
    )

    notification_date = fields.Datetime(
        string="Fecha/hora notificación",
        readonly=True,
    )

    start_datetime = fields.Datetime(
        string="Fecha/hora inicio",
        readonly=True,
        copy=False,
    )

    notified_by_id = fields.Many2one(
        "res.users",
        string="Notificado por",
        readonly=True,
    )

    material_line_ids = fields.One2many(
        "barca.maintenance.workorder.line.material",
        "workorder_line_id",
        string="Materiales / Repuestos / Kits",
    )

    material_count = fields.Integer(
        string="N° materiales",
        compute="_compute_material_count",
    )

    material_summary = fields.Char(
        string="Materiales",
        compute="_compute_material_summary",
    )

    barca_locked_for_executor = fields.Boolean(
        string="Bloqueada para ejecutor",
        compute="_compute_barca_locked_for_executor",
    )

    # -------------------------------------------------------------------------
    # Módulo 4: marcado visual post-devolución
    # -------------------------------------------------------------------------

    # Campos de planificación cuya modificación activa el flag
    _PLANNING_FIELDS = {
        "technical_location_id", "intervention_type_id", "activity_id",
        "estimated_duration", "description", "note", "sequence",
    }

    def _barca_is_restricted_executor(self):
        user = self.env.user
        return (
            user.has_group("zmm_ajustes.group_barca_ejecutor")
            and not user.has_group("zmm_ajustes.group_barca_programador")
            and not user.has_group("zmm_ajustes.group_barca_admin")
        )

    @api.depends("maintenance_request_id.stage_id")
    @api.depends_context("uid")
    def _compute_barca_locked_for_executor(self):
        restricted_executor = self._barca_is_restricted_executor()
        for line in self:
            line.barca_locked_for_executor = (
                restricted_executor
                and line.maintenance_request_id
                and not line.maintenance_request_id._barca_is_stage_in_progress()
            )

    def _barca_check_executor_parent_state(self):
        if not self._barca_is_restricted_executor():
            return

        blocked_lines = self.filtered(
            lambda line: (
                line.maintenance_request_id
                and not line.maintenance_request_id._barca_is_stage_in_progress()
            )
        )
        if blocked_lines:
            raise ValidationError(
                "El ejecutor solo puede modificar actividades cuando la OT esta "
                "en etapa En progreso. Si la OT esta en revision o cerrada, "
                "debe esperar la devolucion del programador."
            )

    @api.model
    def _barca_check_executor_create_parent_state(self, vals_list):
        if not self._barca_is_restricted_executor():
            return

        request_ids = set()
        default_request_id = self.env.context.get("default_maintenance_request_id")
        if default_request_id:
            request_ids.add(default_request_id)

        for vals in vals_list:
            request_id = vals.get("maintenance_request_id")
            if isinstance(request_id, (list, tuple)):
                request_id = request_id[0] if request_id else False
            if request_id:
                request_ids.add(request_id)

        if not request_ids:
            return

        blocked_requests = self.env["maintenance.request"].browse(
            list(request_ids)
        ).filtered(lambda request: not request._barca_is_stage_in_progress())
        if blocked_requests:
            raise ValidationError(
                "El ejecutor solo puede crear actividades cuando la OT esta "
                "en etapa En progreso."
            )

    def _should_mark_after_return(self):
        """True si la OT asociada tiene devoluciones, sigue en ejecución,
        y el usuario es programador o admin.

        Solo en ese contexto tiene sentido marcar actividades como
        modificadas por el programador tras una devolución.
        """
        request = self.maintenance_request_id
        is_planner = (
            self.env.user.has_group("zmm_ajustes.group_barca_programador")
            or self.env.user.has_group("zmm_ajustes.group_barca_admin")
        )
        return (
            bool(request)
            and request.barca_return_count > 0
            and request._barca_is_stage_in_progress()
            and is_planner
        )

    @api.model
    def _barca_get_required_start_labels(self, vals=None):
        vals = vals or {}
        checks = (
            ("technical_location_id", "Ubicacion tecnica"),
            ("intervention_type_id", "Tipo de intervencion"),
            ("activity_id", "Actividad"),
        )
        missing = []
        for field_name, label in checks:
            current = self[field_name].id if self else False
            value = vals.get(field_name, current)
            if isinstance(value, (list, tuple)):
                value = value[0] if value else False
            if not value:
                missing.append(label)
        return missing

    def _barca_check_can_start(self, vals=None):
        for line in self:
            missing = line._barca_get_required_start_labels(vals)
            if missing:
                raise ValidationError(
                    "No se puede iniciar la actividad. Complete primero: %s."
                    % ", ".join(missing)
                )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("state") == "closed":
                vals["state"] = "notified"
            if vals.get("state") == "in_progress":
                missing = self._barca_get_required_start_labels(vals)
                if missing:
                    raise ValidationError(
                        "No se puede iniciar la actividad. Complete primero: %s."
                        % ", ".join(missing)
                    )
        self._barca_check_executor_create_parent_state(vals_list)
        records = super().create(vals_list)
        for record in records:
            if record._should_mark_after_return():
                record.barca_added_after_return = True
        return records

    def write(self, vals):
        if "start_datetime" in vals and not self.env.context.get(
            "allow_barca_activity_start_write"
        ):
            raise ValidationError(
                "La fecha y hora de inicio de la actividad no se puede "
                "modificar manualmente."
            )
        if vals.get("state") == "closed":
            vals = dict(vals, state="notified")
        self._barca_check_executor_parent_state()
        if vals.get("state") == "in_progress":
            self._barca_check_can_start(vals)
        result = super().write(vals)
        if self._PLANNING_FIELDS & set(vals.keys()):
            for record in self:
                if (
                    not record.barca_added_after_return
                    and record._should_mark_after_return()
                ):
                    record.barca_added_after_return = True
        return result

    @api.depends(
        "sequence",
        "maintenance_request_id.name",
        "activity_id.display_name",
        "technical_location_id.display_name",
    )
    def _compute_display_name(self):
        for rec in self:
            parts = []
            if rec.activity_id:
                parts.append(rec.activity_id.display_name)
            if rec.technical_location_id:
                parts.append(rec.technical_location_id.display_name)

            label = " - ".join(parts) or "Actividad OT"
            if rec.sequence:
                label = "[%s] %s" % (rec.sequence, label)
            if rec.maintenance_request_id:
                label = "%s / %s" % (rec.maintenance_request_id.display_name, label)

            rec.display_name = label

    @api.depends("material_line_ids")
    def _compute_material_count(self):
        for rec in self:
            rec.material_count = len(rec.material_line_ids)

    @api.depends(
        "material_line_ids.sequence",
        "material_line_ids.product_id",
        "material_line_ids.product_id.display_name",
        "material_line_ids.estimated_quantity",
        "material_line_ids.product_uom_id",
    )
    def _compute_material_summary(self):
        for rec in self:
            lines = rec.material_line_ids.sorted(lambda line: line.sequence)
            parts = []

            for line in lines[:3]:
                if not line.product_id:
                    continue

                qty = line.estimated_quantity or 0.0
                qty_text = ("%s" % qty).rstrip("0").rstrip(".")
                uom = line.product_uom_id.name or line.product_id.uom_id.name or ""
                parts.append(
                    "%s x%s %s" % (line.product_id.display_name, qty_text, uom)
                )

            if not parts:
                rec.material_summary = False
                continue

            remaining = len(lines) - len(parts)
            summary = ", ".join(parts)
            if remaining > 0:
                summary = "%s (+%s)" % (summary, remaining)

            rec.material_summary = summary

    def action_start_line(self):
        start_datetime = fields.Datetime.now()
        for line in self:
            if line.state != "pending":
                raise ValidationError(
                    "Solo se pueden iniciar actividades en estado Pendiente."
                )
            line._barca_check_can_start()
            line.with_context(allow_barca_activity_start_write=True).write(
                {
                    "state": "in_progress",
                    "start_datetime": start_datetime,
                }
            )
            request = line.maintenance_request_id
            if request and not request.barca_start_datetime:
                request.with_context(
                    allow_barca_workorder_start_write=True
                ).write({"barca_start_datetime": start_datetime})
        return True

    def action_barca_reserve_materials(self):
        self.ensure_one()
        if not self.maintenance_request_id:
            raise ValidationError("La actividad no tiene una OT asociada.")
        return self.maintenance_request_id.action_barca_reserve_materials()

    def action_notify_line(self):
        for line in self:
            if line.state != "in_progress":
                raise ValidationError(
                    "Solo se pueden notificar actividades en estado En ejecución."
                )
            if not line.notification_note or not line.notification_note.strip():
                raise ValidationError(
                    "Debe ingresar la descripción de lo realizado antes de notificar."
                )
            if not line.result:
                raise ValidationError(
                    "Debe seleccionar un resultado antes de notificar la actividad."
                )

            line.material_line_ids._check_quantities_non_negative()
            line.material_line_ids._barca_consume_available_for_notification()
            line.write(
                {
                    "state": "notified",
                    "notification_date": fields.Datetime.now(),
                    "notified_by_id": self.env.user.id,
                }
            )
        return True

    def action_notify_line_open_form(self):
        """Abre el formulario de la actividad en la pestaña Notificación.

        Usado desde la lista de actividades de la OT, donde el usuario
        necesita completar notification_note y result antes de notificar.
        El botón "Notificar" del header del form ejecuta action_notify_line
        una vez que los campos estén completos.
        """
        self.ensure_one()
        if self.state != "in_progress":
            raise ValidationError(
                "Solo se pueden notificar actividades en estado En ejecución."
            )
        return {
            "type": "ir.actions.act_window",
            "name": "Notificar actividad",
            "res_model": "barca.maintenance.workorder.line",
            "view_mode": "form",
            "views": [(False, "form")],
            "res_id": self.id,
            "target": "new",
            "context": {
                "default_maintenance_request_id": self.maintenance_request_id.id,
                "active_tab": "notification",
            },
        }

    def action_close_line(self):
        raise ValidationError(
            "El cierre individual de actividades ya no forma parte del flujo. "
            "Notifique las actividades y cierre la OT parcial o totalmente."
        )

    def action_reset_to_pending(self):
        if not (
            self.env.user.has_group("zmm_ajustes.group_barca_admin")
            or self.env.user.has_group("zmm_ajustes.group_barca_programador")
        ):
            raise ValidationError(
                "Solo un administrador o programador Barca puede reabrir "
                "actividades a pendiente."
            )

        for line in self:
            line.with_context(allow_barca_activity_start_write=True).write(
                {
                    "state": "pending",
                    "start_datetime": False,
                    "notification_date": False,
                    "notified_by_id": False,
                }
            )
        return True


class BarcaMaintenanceWorkorderLineMaterial(models.Model):
    _name = "barca.maintenance.workorder.line.material"
    _description = "Material, repuesto o kit por actividad de OT Barca"
    _order = "sequence, id"

    sequence = fields.Integer(string="Secuencia", default=10)

    workorder_line_id = fields.Many2one(
        "barca.maintenance.workorder.line",
        string="Actividad de OT",
        required=True,
        ondelete="cascade",
        index=True,
    )

    maintenance_request_id = fields.Many2one(
        "maintenance.request",
        string="Orden de Trabajo",
        related="workorder_line_id.maintenance_request_id",
        store=True,
        readonly=True,
    )

    alert_line_material_id = fields.Many2one(
        "barca.maintenance.alert.line.material",
        string="Material del aviso origen",
        ondelete="set null",
    )

    product_id = fields.Many2one(
        "product.product",
        string="Repuesto / Kit / Material",
        required=True,
    )

    product_uom_id = fields.Many2one(
        "uom.uom",
        string="UdM",
        required=True,
    )

    product_uom_category_id = fields.Many2one(
        "uom.category",
        related="product_id.uom_id.category_id",
        readonly=True,
    )

    estimated_quantity = fields.Float(
        string="Cantidad estimada",
        required=True,
        default=1.0,
    )

    requested_quantity = fields.Float(
        string="Cantidad a solicitar a bodega",
        default=0.0,
    )
    available_quantity = fields.Float(
        string="Cantidad disponible Serviteca",
        default=0.0,
    )
    reserved_quantity = fields.Float(string="Cantidad reservada", default=0.0)
    withdrawn_quantity = fields.Float(string="Cantidad retirada", default=0.0)
    consumed_quantity = fields.Float(string="Cantidad consumida", default=0.0)
    returned_quantity = fields.Float(string="Cantidad devuelta", default=0.0)

    note = fields.Text(string="Observación")

    barca_locked_for_executor = fields.Boolean(
        string="Bloqueada para ejecutor",
        compute="_compute_barca_locked_for_executor",
    )

    def _barca_is_restricted_executor(self):
        user = self.env.user
        return (
            user.has_group("zmm_ajustes.group_barca_ejecutor")
            and not user.has_group("zmm_ajustes.group_barca_programador")
            and not user.has_group("zmm_ajustes.group_barca_admin")
        )

    @api.depends("workorder_line_id.maintenance_request_id.stage_id")
    @api.depends_context("uid")
    def _compute_barca_locked_for_executor(self):
        restricted_executor = self._barca_is_restricted_executor()
        for material in self:
            material.barca_locked_for_executor = (
                restricted_executor
                and material.workorder_line_id.maintenance_request_id
                and not material.workorder_line_id.maintenance_request_id._barca_is_stage_in_progress()
            )

    def _barca_check_executor_parent_state(self):
        if not self._barca_is_restricted_executor():
            return

        blocked_materials = self.filtered(
            lambda material: (
                material.workorder_line_id.maintenance_request_id
                and not material.workorder_line_id.maintenance_request_id._barca_is_stage_in_progress()
            )
        )
        if blocked_materials:
            raise ValidationError(
                "El ejecutor solo puede modificar materiales cuando la OT esta "
                "en etapa En progreso. Si la OT esta en revision o cerrada, "
                "debe esperar la devolucion del programador."
            )

    @api.model
    def _barca_check_executor_create_parent_state(self, vals_list):
        if not self._barca_is_restricted_executor():
            return

        line_ids = set()
        default_line_id = self.env.context.get("default_workorder_line_id")
        if default_line_id:
            line_ids.add(default_line_id)

        for vals in vals_list:
            line_id = vals.get("workorder_line_id")
            if isinstance(line_id, (list, tuple)):
                line_id = line_id[0] if line_id else False
            if line_id:
                line_ids.add(line_id)

        if not line_ids:
            return

        blocked_lines = self.env["barca.maintenance.workorder.line"].browse(
            list(line_ids)
        ).filtered(
            lambda line: (
                line.maintenance_request_id
                and not line.maintenance_request_id._barca_is_stage_in_progress()
            )
        )
        if blocked_lines:
            raise ValidationError(
                "El ejecutor solo puede crear materiales cuando la OT esta "
                "en etapa En progreso."
            )

    def _barca_consume_available_for_notification(self):
        for material in self:
            if not material.product_id:
                continue
            available = material.available_quantity or 0.0
            consumed = material.consumed_quantity or 0.0
            if consumed <= 0 and available > 0:
                material.consumed_quantity = available
                consumed = available
            if consumed > available:
                raise ValidationError(
                    "No se puede notificar la actividad porque el consumo del "
                    "material '%s' (%.2f) supera la cantidad disponible en "
                    "Serviteca (%.2f)."
                    % (material.product_id.display_name, consumed, available)
                )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if (
                vals.get("estimated_quantity")
                and "requested_quantity" not in vals
                and "available_quantity" not in vals
            ):
                vals["requested_quantity"] = vals["estimated_quantity"]
        self._barca_check_executor_create_parent_state(vals_list)
        return super().create(vals_list)

    def write(self, vals):
        self._barca_check_executor_parent_state()
        return super().write(vals)

    @api.depends(
        "sequence",
        "workorder_line_id.display_name",
        "product_id.display_name",
        "estimated_quantity",
        "product_uom_id.display_name",
    )
    def _compute_display_name(self):
        for rec in self:
            product = rec.product_id.display_name or "Material OT"
            qty = rec.estimated_quantity or 0.0
            qty_text = ("%s" % qty).rstrip("0").rstrip(".")
            uom = rec.product_uom_id.display_name or ""
            label = "%s x%s %s" % (product, qty_text, uom)
            if rec.workorder_line_id:
                label = "%s / %s" % (rec.workorder_line_id.display_name, label)

            rec.display_name = label

    @api.onchange("estimated_quantity")
    def _onchange_estimated_quantity(self):
        for rec in self:
            if not rec.requested_quantity and not rec.available_quantity:
                rec.requested_quantity = rec.estimated_quantity or 0.0

    @api.onchange("product_id")
    def _onchange_product_id(self):
        for rec in self:
            rec.product_uom_id = rec.product_id.uom_id if rec.product_id else False

    @api.constrains(
        "estimated_quantity",
        "requested_quantity",
        "available_quantity",
        "reserved_quantity",
        "withdrawn_quantity",
        "consumed_quantity",
        "returned_quantity",
    )
    def _check_quantities_non_negative(self):
        quantity_fields = (
            "estimated_quantity",
            "requested_quantity",
            "available_quantity",
            "reserved_quantity",
            "withdrawn_quantity",
            "consumed_quantity",
            "returned_quantity",
        )
        labels = dict(self._fields_get_quantity_labels(quantity_fields))
        for rec in self:
            for field_name in quantity_fields:
                if rec[field_name] < 0:
                    raise ValidationError(
                        "La cantidad '%s' debe ser mayor o igual a cero."
                        % labels[field_name]
                    )

    def _fields_get_quantity_labels(self, quantity_fields):
        for field_name in quantity_fields:
            yield field_name, self._fields[field_name].string

    @api.constrains("product_id", "product_uom_id")
    def _check_product_and_uom(self):
        for rec in self:
            if not rec.product_id:
                raise ValidationError("Debe definir un Repuesto / Kit / Material.")

            if not rec.product_uom_id:
                raise ValidationError("Debe definir una unidad de medida.")

            if rec.product_uom_id.category_id != rec.product_id.uom_id.category_id:
                raise ValidationError(
                    "La unidad de medida debe pertenecer a la misma categoría "
                    "que la unidad del producto."
                )
