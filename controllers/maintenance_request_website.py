from urllib.parse import quote

from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request


MAINTENANCE_REQUEST_FORM_CODE = "solicitud_mantencion"

PRIORITY_LABELS = {
    "low": "Baja",
    "medium": "Media",
    "high": "Alta",
}

VEHICLE_STATUS_LABELS = {
    "operativo": "Operativo",
    "no_operativo": "No operativo",
}

STATE_LABELS = {
    "draft": "Nueva",
    "alert_created": "Aviso creado",
    "cancelled": "Cancelada",
}


class MaintenanceRequestWebsite(http.Controller):

    def _render_template(self, xml_id, values):
        view = request.env.ref(xml_id, raise_if_not_found=False)
        if view and view._name == "ir.ui.view":
            return request.render(view.id, values)
        return request.render(xml_id, values)

    def _get_bearer_token(self):
        auth_header = request.httprequest.headers.get("Authorization", "")
        if auth_header.lower().startswith("bearer "):
            return auth_header[7:].strip()
        return None

    def _get_external_access_token(self, **values):
        return (
            values.get("external_access_token")
            or values.get("access_token")
            or self._get_bearer_token()
            or request.httprequest.cookies.get(
                "zweb_offline_auth_%s" % MAINTENANCE_REQUEST_FORM_CODE
            )
        )

    def _check_external_access(self, access_token=None, mark_used=False):
        return request.env["zweb.offline.form.token.user"].sudo().get_access_token_auth_result(
            access_token,
            form_code=MAINTENANCE_REQUEST_FORM_CODE,
            mark_used=mark_used,
        )

    def _check_form_access(self, access_token=None, mark_used=False):
        if not request.env.user._is_public():
            return {
                "ok": True,
                "auth_method": "odoo_user",
                "user": request.env.user,
            }
        result = self._check_external_access(
            access_token=access_token,
            mark_used=mark_used,
        )
        if result.get("ok"):
            result["auth_method"] = "external_token"
        return result

    def _get_requested_by_id(self, env, access_result):
        if access_result.get("auth_method") == "odoo_user":
            return request.env.user.id
        return env.ref("base.user_admin").id

    def _get_auth_values(self, access_result):
        if access_result.get("auth_method") == "external_token":
            token_user = access_result["token_user"]
            return {
                "external_token_user_id": token_user.id,
                "external_login_snapshot": token_user.login,
                "offline_auth_method": "external_token",
            }
        return {
            "external_token_user_id": False,
            "external_login_snapshot": False,
            "offline_auth_method": "odoo_user",
        }

    def _get_request_domain(self, access_result):
        if access_result.get("auth_method") == "external_token":
            return [("external_token_user_id", "=", access_result["token_user"].id)]
        return [("requested_by_id", "=", request.env.user.id)]

    def _json_access_denied(self, result):
        return {
            "ok": False,
            "error_code": result.get("error_code"),
            "error": result.get("message") or "Acceso denegado.",
        }

    def _render_access_denied(self, result):
        next_url = request.httprequest.full_path or "/solicitud-mantencion"
        if next_url.endswith("?"):
            next_url = next_url[:-1]
        return self._render_template(
            "zmm_ajustes.website_maintenance_request_access_denied",
            {
                "error": result.get("message")
                or "Debe autenticarse para acceder a solicitudes de mantencion.",
                "login_url": "/solicitud-mantencion/login?next=%s"
                % quote(next_url, safe=""),
            },
        )

    def _safe_next_url(self, next_url):
        if not next_url or not next_url.startswith("/solicitud-mantencion"):
            return "/solicitud-mantencion"
        if next_url.startswith("/solicitud-mantencion/login"):
            return "/solicitud-mantencion"
        return next_url

    def _maintenance_request_values(self, extra=None):
        values = {
            "form_code": MAINTENANCE_REQUEST_FORM_CODE,
            "priority_options": list(PRIORITY_LABELS.items()),
            "priority_labels": PRIORITY_LABELS,
            "vehicle_status_options": list(VEHICLE_STATUS_LABELS.items()),
            "vehicle_status_labels": VEHICLE_STATUS_LABELS,
            "state_labels": STATE_LABELS,
        }
        if extra:
            values.update(extra)
        return values

    def _prepare_request_vals(self, env, data, access_result):
        equipment_id = int(data.get("equipment_id") or 0)
        if not equipment_id:
            raise ValidationError("Debe seleccionar un equipo de mantenimiento.")

        equipment = env["maintenance.equipment"].browse(equipment_id)
        if not equipment.exists():
            raise ValidationError("El equipo de mantenimiento seleccionado no existe.")
        if not equipment.vehicle_id:
            raise ValidationError(
                "El equipo de mantenimiento seleccionado no tiene un vehiculo asociado."
            )

        description = str(data.get("description") or "").strip()
        if not description:
            raise ValidationError("Debe describir la necesidad de mantencion.")

        priority = str(data.get("priority") or "medium").strip()
        if priority not in PRIORITY_LABELS:
            priority = "medium"

        vehicle_status = str(data.get("vehicle_status") or "operativo").strip()
        if vehicle_status not in VEHICLE_STATUS_LABELS:
            vehicle_status = "operativo"

        return {
            "equipment_id": equipment.id,
            "priority": priority,
            "vehicle_status": vehicle_status,
            "detailed_location": str(data.get("detailed_location") or "").strip() or False,
            "description": description,
            "requested_by_id": self._get_requested_by_id(env, access_result),
            **self._get_auth_values(access_result),
        }

    @http.route(
        "/solicitud-mantencion/login",
        auth="public",
        website=True,
        sitemap=False,
        methods=["GET"],
    )
    def maintenance_request_login(self, next=None, **kwargs):
        next_url = self._safe_next_url(next)
        access_result = self._check_form_access(
            access_token=self._get_external_access_token(**kwargs),
        )
        if access_result["ok"]:
            return request.redirect(next_url)
        return self._render_template(
            "zmm_ajustes.website_maintenance_request_login",
            {
                "form_code": MAINTENANCE_REQUEST_FORM_CODE,
                "next_url": next_url,
            },
        )

    @http.route("/solicitud-mantencion", auth="public", website=True, sitemap=False)
    def maintenance_request_list(self, **kwargs):
        access_result = self._check_form_access(
            access_token=self._get_external_access_token(**kwargs),
        )
        if not access_result["ok"]:
            return self._render_access_denied(access_result)

        env = request.env(su=True)
        requests = env["barca.maintenance.request"].search(
            self._get_request_domain(access_result),
            order="request_date desc, id desc",
            limit=50,
        )
        return self._render_template(
            "zmm_ajustes.website_maintenance_request_list",
            self._maintenance_request_values({"maintenance_requests": requests}),
        )

    @http.route(
        "/solicitud-mantencion/nueva",
        auth="public",
        website=True,
        sitemap=False,
        methods=["GET"],
    )
    def maintenance_request_new(self, **kwargs):
        access_result = self._check_form_access(
            access_token=self._get_external_access_token(**kwargs),
        )
        if not access_result["ok"]:
            return self._render_access_denied(access_result)

        env = request.env(su=True)
        equipments = env["maintenance.equipment"].search(
            [("vehicle_id", "!=", False)],
            order="name",
        )
        return self._render_template(
            "zmm_ajustes.website_maintenance_request_form",
            self._maintenance_request_values({
                "equipments": equipments,
                "error": None,
                "post": {},
            }),
        )

    @http.route(
        "/solicitud-mantencion/nueva",
        auth="public",
        website=True,
        sitemap=False,
        methods=["POST"],
        csrf=True,
    )
    def maintenance_request_create(self, **post):
        access_result = self._check_form_access(
            access_token=self._get_external_access_token(**post),
            mark_used=True,
        )
        if not access_result["ok"]:
            return self._render_access_denied(access_result)

        env = request.env(su=True)
        equipments = env["maintenance.equipment"].search(
            [("vehicle_id", "!=", False)],
            order="name",
        )
        try:
            vals = self._prepare_request_vals(env, post, access_result)
            maintenance_request = env["barca.maintenance.request"].create(vals)
            return request.redirect("/solicitud-mantencion/%d" % maintenance_request.id)
        except ValidationError as error:
            message = str(error.args[0]) if error.args else "Error de validacion."
        except Exception as error:
            message = "Error al guardar: %s" % str(error)

        return self._render_template(
            "zmm_ajustes.website_maintenance_request_form",
            self._maintenance_request_values({
                "equipments": equipments,
                "error": message,
                "post": post,
            }),
        )

    @http.route(
        "/solicitud-mantencion/<int:maintenance_request_id>",
        auth="public",
        website=True,
        sitemap=False,
        methods=["GET"],
    )
    def maintenance_request_detail(self, maintenance_request_id, **kwargs):
        access_result = self._check_form_access(
            access_token=self._get_external_access_token(**kwargs),
        )
        if not access_result["ok"]:
            return self._render_access_denied(access_result)

        env = request.env(su=True)
        maintenance_request = env["barca.maintenance.request"].search(
            [("id", "=", maintenance_request_id)] + self._get_request_domain(access_result),
            limit=1,
        )
        if not maintenance_request:
            return request.not_found()

        return self._render_template(
            "zmm_ajustes.website_maintenance_request_detail",
            self._maintenance_request_values({
                "maintenance_request": maintenance_request,
            }),
        )

    @http.route(
        "/solicitud-mantencion/sync",
        auth="public",
        type="json",
        methods=["POST"],
        csrf=False,
        website=True,
    )
    def maintenance_request_sync(self, form_code=None, local_uuid=None, payload=None, **kwargs):
        local_uuid = local_uuid or kwargs.get("local_uuid")
        payload = payload or kwargs.get("payload") or {}
        access_result = self._check_form_access(
            access_token=self._get_external_access_token(**kwargs),
            mark_used=True,
        )
        if not access_result["ok"]:
            return self._json_access_denied(access_result)

        if not local_uuid:
            return {"ok": False, "error": "Falta local_uuid"}
        if form_code and form_code != MAINTENANCE_REQUEST_FORM_CODE:
            return {"ok": False, "error": "form_code no reconocido"}
        if not isinstance(payload, dict):
            return {"ok": False, "error": "payload debe ser un objeto"}

        env = request.env(su=True)
        existing = env["barca.maintenance.request"].search(
            [("offline_local_uuid", "=", local_uuid)] + self._get_request_domain(access_result),
            limit=1,
        )
        if existing:
            return {
                "ok": True,
                "duplicate": True,
                "request_id": existing.id,
                "request_name": existing.name,
                "redirect": "/solicitud-mantencion/%d" % existing.id,
            }

        try:
            vals = self._prepare_request_vals(env, payload, access_result)
            vals["offline_local_uuid"] = local_uuid
            maintenance_request = env["barca.maintenance.request"].create(vals)
            return {
                "ok": True,
                "request_id": maintenance_request.id,
                "request_name": maintenance_request.name,
                "redirect": "/solicitud-mantencion/%d" % maintenance_request.id,
            }
        except ValidationError as error:
            return {
                "ok": False,
                "error": str(error.args[0]) if error.args else "Error de validacion.",
            }
        except Exception as error:
            return {"ok": False, "error": "Error al procesar: %s" % str(error)}
