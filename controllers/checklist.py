from odoo import http
from odoo.http import request
from odoo.exceptions import ValidationError


CHECKLIST_TYPE_LABELS = {
    "checklist_camion": "Checklist Camion",
    "checklist_camion_equipo_ap": "Checklist Camion y Equipo AP",
    "checklist_camion_equipo_av": "Checklist Camion y Equipo AV",
    "checklist_vehiculo": "Checklist Vehiculo",
}

VEHICLE_STATUS_LABELS = {
    "operativo": "Operativo",
    "no_operativo": "No operativo",
}

STATE_LABELS = {
    "new": "Nuevo",
    "notice_created": "Aviso generado",
    "closed_no_notice": "Cerrado sin aviso",
    "cancelled": "Cancelado",
}

# Base de datos que sirve las páginas del checklist público.
# Se puede sobrescribir en la URL con ?db=nombre mientras se desarrolla.
_CHECKLIST_DB = "barca-productivo"


def _get_env(db=None):
    """Devuelve un entorno con sudo en la base de datos correcta."""
    target_db = db or request.params.get("db") or _CHECKLIST_DB
    registry = http.request.env.registry
    # Si la request ya está en la DB correcta, usamos su cursor
    if registry.db_name == target_db:
        return request.env(su=True)
    # Si no, abrimos un cursor nuevo en la DB destino
    import odoo
    new_reg = odoo.registry(target_db)
    cr = new_reg.cursor()
    env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
    # Adjuntamos el cursor al request para que se cierre al finalizar
    request._checklist_cr = cr
    return env


class ChecklistWebsite(http.Controller):

    @http.route("/checklist", auth="public", website=True, sitemap=False)
    def checklist_list(self, db=None, **kwargs):
        env = request.env(su=True)
        checklists = env["barca.maintenance.checklist"].search(
            [], order="checklist_date desc, id desc", limit=50
        )
        return request.render(
            "zmm_ajustes.website_checklist_list",
            {
                "checklists": checklists,
                "state_labels": STATE_LABELS,
                "checklist_type_labels": CHECKLIST_TYPE_LABELS,
                "vehicle_status_labels": VEHICLE_STATUS_LABELS,
            },
        )

    @http.route("/checklist/nuevo", auth="public", website=True, sitemap=False, methods=["GET"])
    def checklist_new(self, db=None, **kwargs):
        env = request.env(su=True)
        vehicles = env["fleet.vehicle"].search([], order="name")
        return request.render(
            "zmm_ajustes.website_checklist_form",
            {
                "checklist": None,
                "vehicles": vehicles,
                "checklist_types": list(CHECKLIST_TYPE_LABELS.items()),
                "vehicle_status_options": list(VEHICLE_STATUS_LABELS.items()),
                "state_labels": STATE_LABELS,
                "error": None,
                "success": None,
            },
        )

    @http.route("/checklist/nuevo", auth="public", website=True, sitemap=False, methods=["POST"], csrf=True)
    def checklist_create(self, db=None, **post):
        env = request.env(su=True)
        vehicles = env["fleet.vehicle"].search([], order="name")
        error = None
        try:
            vehicle_id = int(post.get("vehicle_id") or 0)
            checklist_type = post.get("checklist_type", "").strip()

            if not vehicle_id:
                raise ValidationError("Debe seleccionar un equipo.")
            if not checklist_type:
                raise ValidationError("Debe seleccionar el tipo de vehículo.")

            items = env["barca.maintenance.checklist.item"].search(
                [("checklist_type", "=", checklist_type), ("active", "=", True)]
            )

            line_commands = []
            for item in items:
                yes_val = post.get("yes_%d" % item.id) == "1"
                no_val = post.get("no_%d" % item.id) == "1"
                if yes_val and no_val:
                    no_val = False
                line_commands.append((0, 0, {
                    "item_template_id": item.id,
                    "control_type": item.control_type,
                    "control_item": item.control_item,
                    "sequence": item.sequence,
                    "yes": yes_val,
                    "no": no_val,
                }))

            requested_by = (
                request.env.user.id
                if not request.env.user._is_public()
                else env.ref("base.user_admin").id
            )

            vals = {
                "vehicle_id": vehicle_id,
                "checklist_type": checklist_type,
                "vehicle_status": post.get("vehicle_status", "operativo"),
                "detailed_location": post.get("detailed_location", "").strip() or False,
                "observations": post.get("observations", "").strip() or False,
                "requested_by_id": requested_by,
                "line_ids": line_commands,
            }
            fuel_raw = post.get("fuel_load_time", "").strip()
            if fuel_raw:
                try:
                    vals["fuel_load_time"] = float(fuel_raw.replace(",", "."))
                except ValueError:
                    pass
            odometer_raw = post.get("odometer", "").strip()
            if odometer_raw:
                try:
                    vals["odometer"] = float(odometer_raw.replace(",", "."))
                except ValueError:
                    pass

            checklist = env["barca.maintenance.checklist"].create(vals)
            return request.redirect("/checklist/%d" % checklist.id)

        except ValidationError as e:
            error = str(e.args[0]) if e.args else "Error de validación."
        except Exception as e:
            error = "Error al guardar: %s" % str(e)

        return request.render(
            "zmm_ajustes.website_checklist_form",
            {
                "checklist": None,
                "vehicles": vehicles,
                "checklist_types": list(CHECKLIST_TYPE_LABELS.items()),
                "vehicle_status_options": list(VEHICLE_STATUS_LABELS.items()),
                "state_labels": STATE_LABELS,
                "error": error,
                "success": None,
                "post": post,
            },
        )

    @http.route("/checklist/<int:checklist_id>", auth="public", website=True, sitemap=False, methods=["GET"])
    def checklist_detail(self, checklist_id, db=None, **kwargs):
        env = request.env(su=True)
        checklist = env["barca.maintenance.checklist"].browse(checklist_id)
        if not checklist.exists():
            return request.not_found()
        return request.render(
            "zmm_ajustes.website_checklist_detail",
            {
                "checklist": checklist,
                "state_labels": STATE_LABELS,
                "checklist_type_labels": CHECKLIST_TYPE_LABELS,
                "vehicle_status_labels": VEHICLE_STATUS_LABELS,
                "error": None,
                "success": None,
            },
        )

    @http.route("/checklist/<int:checklist_id>", auth="public", website=True, sitemap=False, methods=["POST"], csrf=True)
    def checklist_detail_save(self, checklist_id, db=None, **post):
        env = request.env(su=True)
        checklist = env["barca.maintenance.checklist"].browse(checklist_id)
        if not checklist.exists():
            return request.not_found()

        error = None
        success = None
        if checklist.state != "new":
            error = "Solo se pueden editar checklists en estado Nuevo."
        else:
            try:
                for line in checklist.line_ids:
                    yes_val = post.get("yes_%d" % line.id) == "1"
                    no_val = post.get("no_%d" % line.id) == "1"
                    if yes_val and no_val:
                        no_val = False
                    line.write({"yes": yes_val, "no": no_val})
                checklist._auto_process_after_save()
                success = "Puntos de control guardados correctamente."
                checklist = env["barca.maintenance.checklist"].browse(checklist_id)
            except ValidationError as e:
                error = str(e.args[0]) if e.args else "Error de validación."
            except Exception as e:
                error = "Error al guardar: %s" % str(e)

        return request.render(
            "zmm_ajustes.website_checklist_detail",
            {
                "checklist": checklist,
                "state_labels": STATE_LABELS,
                "checklist_type_labels": CHECKLIST_TYPE_LABELS,
                "vehicle_status_labels": VEHICLE_STATUS_LABELS,
                "error": error,
                "success": success,
            },
        )

    @http.route("/checklist/items/<string:checklist_type>", auth="public", type="json", methods=["POST"])
    def checklist_items_json(self, checklist_type, db=None, **kwargs):
        env = request.env(su=True)
        items = env["barca.maintenance.checklist.item"].search(
            [("checklist_type", "=", checklist_type), ("active", "=", True)],
            order="sequence, id",
        )
        return [
            {
                "id": item.id,
                "control_type": item.control_type,
                "control_item": item.control_item,
                "sequence": item.sequence,
            }
            for item in items
        ]

    @http.route(
        "/checklist/sync",
        auth="public",
        type="json",
        methods=["POST"],
        csrf=False,
        website=True,
    )
    def checklist_sync(self, form_code=None, local_uuid=None, payload=None, **kwargs):
        """Recibe un payload de checklist guardado offline y crea el registro en BD.

        Endpoint JSON sin CSRF para que el motor offline pueda hacer POST
        tras recuperar la conexión, sin depender de un token CSRF fresco.
        En rutas type='json' de Odoo 18 los parámetros llegan directamente
        como argumentos de la función (params del JSON-RPC).
        """
        local_uuid = local_uuid or kwargs.get("local_uuid")
        payload = payload or kwargs.get("payload") or {}

        if not local_uuid:
            return {"ok": False, "error": "Falta local_uuid"}
        if form_code and form_code != "checklist_nuevo":
            return {"ok": False, "error": "form_code no reconocido"}
        if not isinstance(payload, dict):
            return {"ok": False, "error": "payload debe ser un objeto"}

        env = request.env(su=True)

        # Idempotencia: si ya sincronizamos este UUID, devolvemos el resultado previo.
        existing = env["barca.maintenance.checklist"].search(
            [("offline_local_uuid", "=", local_uuid)], limit=1
        )
        if existing:
            return {
                "ok": True,
                "duplicate": True,
                "checklist_id": existing.id,
                "checklist_name": existing.name,
                "redirect": "/checklist/%d" % existing.id,
            }

        try:
            vehicle_id = int(payload.get("vehicle_id") or 0)
            checklist_type = str(payload.get("checklist_type") or "").strip()

            if not vehicle_id:
                return {"ok": False, "error": "Debe seleccionar un equipo."}
            if not checklist_type:
                return {"ok": False, "error": "Debe seleccionar el tipo de vehículo."}

            items = env["barca.maintenance.checklist.item"].search(
                [("checklist_type", "=", checklist_type), ("active", "=", True)]
            )

            line_commands = []
            for item in items:
                yes_val = payload.get("yes_%d" % item.id) == "1"
                no_val = payload.get("no_%d" % item.id) == "1"
                if yes_val and no_val:
                    no_val = False
                line_commands.append((0, 0, {
                    "item_template_id": item.id,
                    "control_type": item.control_type,
                    "control_item": item.control_item,
                    "sequence": item.sequence,
                    "yes": yes_val,
                    "no": no_val,
                }))

            vals = {
                "vehicle_id": vehicle_id,
                "checklist_type": checklist_type,
                "vehicle_status": payload.get("vehicle_status", "operativo"),
                "detailed_location": str(payload.get("detailed_location") or "").strip() or False,
                "observations": str(payload.get("observations") or "").strip() or False,
                "requested_by_id": env.ref("base.user_admin").id,
                "line_ids": line_commands,
            }

            # Guardar el UUID local para idempotencia en sync repetidos.
            if "offline_local_uuid" in env["barca.maintenance.checklist"]._fields:
                vals["offline_local_uuid"] = local_uuid

            fuel_raw = str(payload.get("fuel_load_time") or "").strip()
            if fuel_raw:
                try:
                    vals["fuel_load_time"] = float(fuel_raw.replace(",", "."))
                except ValueError:
                    pass
            odometer_raw = str(payload.get("odometer") or "").strip()
            if odometer_raw:
                try:
                    vals["odometer"] = float(odometer_raw.replace(",", "."))
                except ValueError:
                    pass

            checklist = env["barca.maintenance.checklist"].create(vals)

            return {
                "ok": True,
                "checklist_id": checklist.id,
                "checklist_name": checklist.name,
                "redirect": "/checklist/%d" % checklist.id,
            }

        except ValidationError as e:
            return {"ok": False, "error": str(e.args[0]) if e.args else "Error de validación."}
        except Exception as e:
            return {"ok": False, "error": "Error al procesar: %s" % str(e)}
