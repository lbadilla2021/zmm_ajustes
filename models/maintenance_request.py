from collections import defaultdict

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class MaintenanceRequest(models.Model):
    _inherit = "maintenance.request"

    # La OT gestiona su propio ciclo de programación, ejecución, revisión y cierre.
    # El aviso asociado permanece en "Con OT creada" hasta que el usuario lo cierre
    # explícitamente, una vez que la OT esté en una etapa terminada.

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

    def action_barca_reserve_materials(self):
        """Crea una reserva de materiales (stock.picking) vinculada a la OT.

        - Agrupa materiales por producto/UdM.
        - Confirma y asigna el picking (no lo valida).
        - Actualiza reserved_quantity en las líneas de material.
        - Publica resumen en chatter.
        """
        self.ensure_one()

        # --- Validación: reserva duplicada o picking en estado inválido ---
        if self.barca_material_picking_id:
            picking = self.barca_material_picking_id
            if picking.exists() and picking.state not in ("cancel",):
                raise ValidationError(
                    "Esta OT ya tiene una reserva de materiales vinculada (ref: %s). "
                    "No se puede crear una segunda reserva." % picking.name
                )
            # El picking fue cancelado o borrado: limpiar el vínculo y continuar
            self.write({
                "barca_material_picking_id": False,
                "barca_material_state": "pending_reservation",
            })
            self.message_post(
                body=(
                    "La reserva anterior (<b>%s</b>) estaba cancelada o fue eliminada. "
                    "Se ha limpiado el vínculo para permitir una nueva reserva."
                ) % (picking.name if picking.exists() else "eliminada")
            )

        # --- Recolectar materiales válidos ---
        all_material_lines = self.env["barca.maintenance.workorder.line.material"]
        for activity in self.barca_activity_line_ids:
            for mat in activity.material_line_ids:
                if mat.product_id and mat.estimated_quantity > 0:
                    if not mat.product_uom_id:
                        raise ValidationError(
                            "El material '%s' no tiene unidad de medida definida."
                            % mat.product_id.display_name
                        )
                    all_material_lines |= mat

        if not all_material_lines:
            self.write({"barca_material_state": "no_materials"})
            if callable(getattr(self, "message_post", None)):
                self.message_post(
                    body="No se encontraron materiales válidos para reservar en esta OT."
                )
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Sin materiales",
                    "message": "No hay materiales con cantidad estimada mayor a cero.",
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

        # Ubicación destino: buscar una ubicación interna destinada a mantenimiento
        location_dest = self.env["stock.location"].search(
            [
                ("usage", "=", "internal"),
                ("active", "=", True),
                ("complete_name", "ilike", "WH/Serviteca"),
                ("company_id", "in", [company.id, False]),
            ],
            limit=1,        )
        if not location_dest:
            # Usar la ubicación destino por defecto del tipo de operación
            location_dest = picking_type.default_location_dest_id
        if not location_dest or location_dest.id == location_src.id:
            raise ValidationError(
                "No se pudo determinar una ubicación destino para la reserva de mantenimiento. "
                "Cree una ubicación interna llamada 'Mantenimiento' o configure la ubicación "
                "destino por defecto del tipo de operación '%s'." % picking_type.name
            )

        # --- Agrupar materiales por (product_id, product_uom_id) ---
        # Estructura: {(product_id, uom_id): qty_total}
        grouped_qty = defaultdict(float)
        for mat in all_material_lines:
            key = (mat.product_id.id, mat.product_uom_id.id)
            grouped_qty[key] += mat.estimated_quantity

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
                if mat.product_id and mat.estimated_quantity > 0 and mat.product_uom_id:
                    key = (mat.product_id.id, mat.product_uom_id.id)
                    lines_by_key[key].append(mat)

        for key, lines in lines_by_key.items():
            available = reserved_by_key.get(key, 0.0)
            for mat in lines:
                assignable = min(mat.estimated_quantity, available)
                assignable = max(assignable, 0.0)
                mat.write({"reserved_quantity": assignable})
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
        """Retorna todas las líneas de material de la OT que tienen product_id.

        Nota: no lleva ensure_one() porque es llamado desde _compute_barca_material_costs
        dentro de un for rec in self. La garantía de singleton la dan los callers.
        """
        lines = self.env["barca.maintenance.workorder.line.material"]
        for activity in self.barca_activity_line_ids:
            for mat in activity.material_line_ids:
                if mat.product_id:
                    lines |= mat
        return lines

    def action_barca_deliver_materials(self):
        """Registra la entrega de materiales al técnico.

        - Si existe reserved_quantity > 0, usa ese valor como withdrawn_quantity.
        - Si no hay reserva previa, usa estimated_quantity.
        - Marca barca_material_withdrawn = True y registra fecha/usuario.
        """
        self.ensure_one()

        material_lines = self._barca_get_material_lines()
        if not material_lines:
            raise ValidationError(
                "No hay materiales asociados a las actividades de esta OT."
            )

        if self.barca_material_withdrawn:
            raise ValidationError(
                "Los materiales de esta OT ya fueron entregados."
            )

        used_reservation = False
        total_estimated = 0.0
        total_reserved = 0.0
        total_delivered = 0.0

        for mat in material_lines:
            if mat.reserved_quantity > 0:
                withdrawn = mat.reserved_quantity
                used_reservation = True
            else:
                withdrawn = mat.estimated_quantity or 0.0

            if withdrawn < 0:
                raise ValidationError(
                    "La cantidad a entregar del producto '%s' no puede ser negativa."
                    % (mat.product_id.display_name or "desconocido")
                )

            mat.write({"withdrawn_quantity": withdrawn})
            total_estimated += mat.estimated_quantity or 0.0
            total_reserved += mat.reserved_quantity or 0.0
            total_delivered += withdrawn

        self.write(
            {
                "barca_material_withdrawn": True,
                "barca_material_delivery_date": fields.Datetime.now(),
                "barca_material_delivered_by_id": self.env.user.id,
            }
        )

        if used_reservation:
            base_msg = "Se usó la <b>cantidad reservada</b> como base de entrega."
        else:
            base_msg = (
                "No había reserva previa. "
                "Se usó la <b>cantidad estimada</b> como base de entrega."
            )

        body = (
            "<b>Materiales entregados</b><br/>"
            "Líneas de materiales: <b>%s</b><br/>"
            "Cantidad total estimada: <b>%.2f</b><br/>"
            "Cantidad total reservada: <b>%.2f</b><br/>"
            "Cantidad total entregada: <b>%.2f</b><br/>"
            "%s"
        ) % (
            len(material_lines),
            total_estimated,
            total_reserved,
            total_delivered,
            base_msg,
        )
        self.message_post(body=body)

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Materiales entregados",
                "message": "Se registró la entrega de %s líneas de materiales."
                % len(material_lines),
                "type": "success",
                "sticky": False,
            },
        }

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

        if not self.barca_material_withdrawn:
            raise ValidationError(
                "Primero debe registrar la entrega de materiales antes de cerrar el ciclo."
            )

        if self.barca_material_closed:
            raise ValidationError(
                "El ciclo de materiales de esta OT ya está cerrado."
            )

        # Validaciones de cantidades y cálculo de sobrante
        for mat in material_lines:
            product_name = mat.product_id.display_name or "desconocido"
            for field_name, label in (
                ("estimated_quantity", "estimada"),
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
            withdrawn = mat.withdrawn_quantity or 0.0
            if consumed > withdrawn:
                raise ValidationError(
                    "El consumo real del producto '%s' (%.2f) no puede ser mayor "
                    "que la cantidad entregada (%.2f)."
                    % (product_name, consumed, withdrawn)
                )

        # Calcular sobrante, escribir y acumular costos en el mismo loop
        total_withdrawn = 0.0
        total_consumed = 0.0
        total_returned = 0.0
        estimated_cost = 0.0
        real_cost = 0.0

        for mat in material_lines:
            consumed = mat.consumed_quantity or 0.0
            withdrawn = mat.withdrawn_quantity or 0.0
            returned = withdrawn - consumed
            returned = max(returned, 0.0)
            mat.write({"returned_quantity": returned})
            total_withdrawn += withdrawn
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
    }

    barca_state = fields.Selection(
        [
            ("in_progress", "En ejecución"),
            ("under_review", "En revisión"),
            ("approved", "Aprobada"),
        ],
        string="Estado Barca",
        default="in_progress",
        tracking=True,
        copy=False,
    )

    barca_locked_for_executor = fields.Boolean(
        string="Bloqueada para ejecutor",
        compute="_compute_barca_locked_for_executor",
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
                    lambda line: line.state in ("notified", "closed")
                )
            )
            closed = len(
                request.barca_activity_line_ids.filtered(
                    lambda line: line.state == "closed"
                )
            )

            request.barca_activity_count = total
            request.barca_total_activity_count = total
            request.barca_notified_activity_count = notified
            request.barca_closed_activity_count = closed
            request.barca_all_activities_notified = total > 0 and notified == total
            request.barca_all_activities_closed = total > 0 and closed == total

    def _barca_is_restricted_executor(self):
        user = self.env.user
        return (
            user.has_group("zmm_ajustes.group_barca_ejecutor")
            and not user.has_group("zmm_ajustes.group_barca_programador")
            and not user.has_group("zmm_ajustes.group_barca_admin")
        )

    @api.depends("barca_state")
    @api.depends_context("uid")
    def _compute_barca_locked_for_executor(self):
        restricted_executor = self._barca_is_restricted_executor()
        for request in self:
            request.barca_locked_for_executor = (
                restricted_executor and request.barca_state != "in_progress"
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
            "barca_state" in vals
            and not self.env.context.get("allow_barca_executor_state_write")
        ):
            raise ValidationError(
                "El ejecutor no puede cambiar manualmente el estado de revision "
                "de la OT. Use las acciones disponibles."
            )

        blocked_requests = self.filtered(
            lambda request: request.barca_state != "in_progress"
        )
        if blocked_requests:
            raise ValidationError(
                "El ejecutor solo puede editar una OT cuando esta en estado "
                "En ejecucion. Si la OT esta en revision o aprobada, debe "
                "esperar la devolucion del programador."
            )

    def write(self, vals):
        self._barca_check_executor_write_access(vals)
        return super().write(vals)

    def action_barca_send_to_review(self):
        """Envía la OT a revisión del programador.

        El revisor se resuelve automáticamente: es el usuario que tomó
        el aviso para evaluación (barca_alert_id.approved_by_id).
        Si la OT no tiene aviso asociado, se usa el create_uid de la OT.
        No requiere que el jefe de taller asigne un revisor manualmente.
        """
        self.ensure_one()

        if self.barca_state != "in_progress":
            raise ValidationError(
                "Solo se puede enviar a revisión una OT en estado En ejecución."
            )
        if not self.barca_activity_line_ids:
            raise ValidationError(
                "La OT debe tener al menos una actividad para enviarse a revisión."
            )
        pending_lines = self.barca_activity_line_ids.filtered(
            lambda line: line.state not in ("notified", "closed")
        )
        if pending_lines:
            raise ValidationError(
                "Todas las actividades deben estar notificadas antes de enviar "
                "la OT a revisión. Actividades pendientes: %s."
                % ", ".join(l.activity_id.name or str(l.id) for l in pending_lines)
            )

        # Resolver revisor automáticamente desde el aviso origen
        reviewer = (
            self.barca_alert_id.approved_by_id
            if self.barca_alert_id and self.barca_alert_id.approved_by_id
            else self.create_uid
        )
        self.with_context(allow_barca_executor_state_write=True).write(
            {
                "barca_state": "under_review",
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

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "OT enviada a revisión",
                "message": "Se notificó a %s." % reviewer.name,
                "type": "success",
                "sticky": False,
            },
        }

    def action_barca_approve(self):
        """Aprueba la OT. Solo programador y admin.

        Notifica al responsable de ejecución (user_id de la OT).
        Limpia los flags barca_added_after_return de las actividades.
        """
        self.ensure_one()

        if self.barca_state != "under_review":
            raise ValidationError(
                "Solo se puede aprobar una OT que esté en revisión."
            )

        self.write({"barca_state": "approved"})

        # Limpiar marcas visuales de actividades post-devolución
        self.barca_activity_line_ids.filtered(
            lambda l: l.barca_added_after_return
        ).write({"barca_added_after_return": False})

        # Notificar al responsable de ejecución
        responsible = self.user_id
        partner_ids = responsible.partner_id.ids if responsible else []
        self.message_post(
            body=(
                "<b>OT aprobada</b><br/>"
                "Aprobada por: <b>%s</b>"
            ) % self.env.user.name,
            partner_ids=partner_ids,
        )

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "OT aprobada",
                "message": "La OT ha sido aprobada.",
                "type": "success",
                "sticky": False,
            },
        }

    def action_barca_return_to_progress(self):
        """Devuelve la OT a ejecución. Solo programador y admin.

        Requiere motivo de devolución. Notifica al responsable de ejecución.
        Incrementa barca_return_count para el marcado visual del módulo 4.
        """
        self.ensure_one()

        if self.barca_state != "under_review":
            raise ValidationError(
                "Solo se puede devolver una OT que esté en revisión."
            )
        if not self.barca_return_reason or not self.barca_return_reason.strip():
            raise ValidationError(
                "Debe ingresar el motivo de devolución antes de devolver la OT."
            )

        self.write({
            "barca_state": "in_progress",
            "barca_return_count": self.barca_return_count + 1,
        })

        # Notificar al responsable de ejecución
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

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "OT devuelta a ejecución",
                "message": "Se notificó a %s." % (responsible.name if responsible else "nadie"),
                "type": "warning",
                "sticky": False,
            },
        }


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
            ("closed", "Cerrada"),
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

    @api.depends("maintenance_request_id.barca_state")
    @api.depends_context("uid")
    def _compute_barca_locked_for_executor(self):
        restricted_executor = self._barca_is_restricted_executor()
        for line in self:
            line.barca_locked_for_executor = (
                restricted_executor
                and line.maintenance_request_id.barca_state != "in_progress"
            )

    def _barca_check_executor_parent_state(self):
        if not self._barca_is_restricted_executor():
            return

        blocked_lines = self.filtered(
            lambda line: line.maintenance_request_id.barca_state != "in_progress"
        )
        if blocked_lines:
            raise ValidationError(
                "El ejecutor solo puede modificar actividades cuando la OT esta "
                "en estado En ejecucion. Si la OT esta en revision o aprobada, "
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
        ).filtered(lambda request: request.barca_state != "in_progress")
        if blocked_requests:
            raise ValidationError(
                "El ejecutor solo puede crear actividades cuando la OT esta "
                "en estado En ejecucion."
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
            and request.barca_state == "in_progress"
            and is_planner
        )

    @api.model_create_multi
    def create(self, vals_list):
        self._barca_check_executor_create_parent_state(vals_list)
        records = super().create(vals_list)
        for record in records:
            if record._should_mark_after_return():
                record.barca_added_after_return = True
        return records

    def write(self, vals):
        self._barca_check_executor_parent_state()
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
        for line in self:
            if line.state != "pending":
                raise ValidationError(
                    "Solo se pueden iniciar actividades en estado Pendiente."
                )
            line.state = "in_progress"
        return True

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
        for line in self:
            if line.state != "notified":
                raise ValidationError(
                    "Solo se pueden cerrar actividades en estado Notificada."
                )
            line.state = "closed"
        return True

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
            line.write(
                {
                    "state": "pending",
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

    @api.depends("workorder_line_id.maintenance_request_id.barca_state")
    @api.depends_context("uid")
    def _compute_barca_locked_for_executor(self):
        restricted_executor = self._barca_is_restricted_executor()
        for material in self:
            material.barca_locked_for_executor = (
                restricted_executor
                and material.workorder_line_id.maintenance_request_id.barca_state
                != "in_progress"
            )

    def _barca_check_executor_parent_state(self):
        if not self._barca_is_restricted_executor():
            return

        blocked_materials = self.filtered(
            lambda material: (
                material.workorder_line_id.maintenance_request_id.barca_state
                != "in_progress"
            )
        )
        if blocked_materials:
            raise ValidationError(
                "El ejecutor solo puede modificar materiales cuando la OT esta "
                "en estado En ejecucion. Si la OT esta en revision o aprobada, "
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
            lambda line: line.maintenance_request_id.barca_state != "in_progress"
        )
        if blocked_lines:
            raise ValidationError(
                "El ejecutor solo puede crear materiales cuando la OT esta "
                "en estado En ejecucion."
            )

    @api.model_create_multi
    def create(self, vals_list):
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

    @api.onchange("product_id")
    def _onchange_product_id(self):
        for rec in self:
            rec.product_uom_id = rec.product_id.uom_id if rec.product_id else False

    @api.constrains(
        "estimated_quantity",
        "reserved_quantity",
        "withdrawn_quantity",
        "consumed_quantity",
        "returned_quantity",
    )
    def _check_quantities_non_negative(self):
        quantity_fields = (
            "estimated_quantity",
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
