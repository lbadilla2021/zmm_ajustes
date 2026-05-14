# AGENTS.md

## Alcance
Estas instrucciones aplican a todo el módulo Odoo `zmm_ajustes`.

## Contexto del módulo
- El módulo se llama **Barca Mantenimiento** y su menú raíz visible en Odoo es **Mantención Barca**.
- La definición principal de acciones y menús está en `views/base_views.xml`.
- La definición de **Avisos** está en `views/maintenance_alert_views.xml`.
- La acción de **Planes de Mantenimiento** está en `views/maintenance_plan_views.xml`.
- La nueva **Solicitud de Mantención** simple está en `models/maintenance_request_simple.py` y `views/maintenance_request_simple_views.xml`.
- El **Checklist** operativo está en `models/maintenance_checklist.py` y `views/maintenance_checklist_views.xml`.
- El reporte **Solicitudes de mantenimiento** del menú **Informes** usa `action_barca_maintenance_request_report` en `views/base_views.xml`.

## Memoria funcional vigente
- Al abrir el módulo **Mantención Barca** o al hacer clic en el menú raíz **Mantención Barca**, debe abrirse **Calendario Mantenimiento** mediante `action_barca_maintenance_calendar`.
- Los menús principales bajo **Mantención Barca** deben quedar en este orden:
  1. **Orígenes Avisos**
  2. **Mantenimiento**
  3. **Informes**
  4. **Equipos**
  5. **Configuración**
- Dentro del menú principal **Orígenes Avisos**, los submenús deben quedar en este orden:
  1. **Planes de Mantenimiento**
  2. **Solicitud de Mantención**
  3. **Checklist**
- Dentro del menú principal **Mantenimiento**, los submenús deben quedar en este orden:
  1. **Avisos**
  2. **Orden de Trabajo**
  3. **Calendario Mantenimiento**
- Dentro del menú principal **Informes**, debe existir **Solicitudes de mantenimiento** mediante `action_barca_maintenance_request_report`.
- **Avisos** no debe quedar como menú principal; debe depender de `menu_barca_maintenance`.
- **Planes de Mantenimiento**, **Solicitud de Mantención** y **Checklist** no deben depender de `menu_barca_maintenance`; deben depender de `menu_barca_alert_origins`.
- La antigua opción basada en `maintenance.request` conserva los XML IDs existentes (`action_barca_maintenance_report`, `menu_barca_reporting_requests`) y se muestra visualmente como **Orden de Trabajo**. No renombrar su modelo técnico ni romper referencias existentes.
- **Solicitud de Mantención** es el requerimiento simple inicial (`barca.maintenance.request`), no la OT estándar. Debe ubicarse bajo **Orígenes Avisos** y puede generar un `barca.maintenance.alert` con origen `request`.
- En **Solicitud de Mantención**, la fecha es la fecha actual y queda bloqueada; el equipo de mantenimiento queda bloqueado y se carga automáticamente desde el vehículo; existen los campos **Planta y Lugar detallado** y **Estado del vehículo** (`operativo` / `no_operativo`).
- **Checklist** (`barca.maintenance.checklist`) es una fuente de avisos bajo **Orígenes Avisos**; sus puntos se cargan desde el catálogo `barca.maintenance.checklist.item` por tipo de vehículo, guarda respuestas **Sí/No**, y al guardar genera automáticamente un aviso si existe al menos un **No**.
- El catálogo de ítems de Checklist se administra desde **Configuración → Checklist** y debe mostrar/editar tipo de vehículo, tipo de control e ítem de control.
- El menú de equipos debe mostrarse como **Equipos** en plural.


## Memoria funcional vigente — Flotilla
- La ampliación productiva de Flotilla está en `models/fleet_vehicle.py`, `views/fleet_vehicle_views.xml`, `models/fleet_alert_rule.py`, `views/fleet_alert_rule_views.xml`, `models/fleet_vehicle_log_contract.py`, `views/fleet_vehicle_log_contract_views.xml` y los datos `data/fleet_alert_rule_data.xml` / `data/cron_fleet_expiration_alerts.xml`.
- En `fleet.vehicle`, el código interno (`x_internal_code`) es calculado y de solo lectura; se deriva de los dos últimos dígitos presentes en la patente (`license_plate`).
- En el formulario de vehículo se ocultan campos estándar no usados por Barca (`future_driver_id`, `plan_to_change_car`, `order_date`, `manager_id` y `mobility_card` de `hr_fleet`); `location` se reubica después de `next_assignation_date`.
- En `fleet.vehicle`, la licencia de conducir (`x_driver_license_expiration_date`) se calcula desde el empleado vinculado al conductor (`work_contact_id` o `address_home_id`) y usa `hr.employee.driver_license_expiration_date` de `zhr_ajustes`.
- La casilla `x_has_insurance_contract` es calculada/solo lectura y se marca si existe un contrato del vehículo cuyo subtipo de costo contiene “seguro”. No editarla manualmente.
- La pestaña estándar fiscal del vehículo fue reemplazada visualmente por **Documentación** y contiene vencimiento de permiso de circulación, vencimiento de revisión técnica, tarjeta combustible, TAG, días de alerta y el botón **Enviar Avisos**.
- El botón **Enviar Avisos** y el cron `ir_cron_send_fleet_expiration_alerts` ejecutan la misma lógica: revisan licencia de conducir, permiso de circulación y revisión técnica próximos a vencer según `x_alert_days_before` por vehículo, y envían correo a destinatarios de la regla `Vencimientos`.
- Al modificar `x_doc_fuel_card` o `x_doc_tag`, se envía correo de cambios documentales a la regla `Modificaciones`; si no hay destinatarios configurados no se envía nada.
- Las reglas/listas de distribución de flotilla son `barca.fleet.alert.rule`; por defecto deben existir `Modificaciones` y `Vencimientos`, creadas/aseguradas por `data/fleet_alert_rule_data.xml`.
- El menú **Alertas** de flotilla aparece en **Mantención Barca → Configuración** para `group_barca_admin` y también en la configuración estándar de Flotilla para `fleet.fleet_group_manager` y `group_barca_admin`.
- Los contratos estándar de flotilla (`fleet.vehicle.log.contract`) permiten adjuntos múltiples mediante `attachment_ids` visible después de notas.
- `fleet.vehicle.log.services` tiene un campo `name` de compatibilidad para vistas de búsqueda que lo esperan.

## Convenciones de cambios
- Mantener los XML IDs existentes cuando se reorganicen menús para no romper actualizaciones de instalaciones existentes.
- Validar XML después de editar vistas o menús.
- Revisar que no se introduzcan XML IDs duplicados en `views/*.xml`.
- Si se documenta una decisión funcional del módulo, actualizar también los documentos relevantes en `docs_codex/`.
