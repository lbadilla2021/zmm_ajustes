# AGENTS.md

## Alcance
Estas instrucciones aplican a todo el módulo Odoo `zmm_ajustes`.

## Contexto del módulo
- El módulo se llama **Barca Mantenimiento** y su menú raíz visible en Odoo es **Mantención Barca**.
- La definición principal de acciones y menús está en `views/base_views.xml`.
- La definición de **Avisos** está en `views/maintenance_alert_views.xml`.
- La acción de **Planes de Mantenimiento** está en `views/maintenance_plan_views.xml`.
- La nueva **Solicitud de Mantención** simple está en `models/maintenance_request_simple.py` y `views/maintenance_request_simple_views.xml`.

## Memoria funcional vigente
- Al abrir el módulo **Mantención Barca** o al hacer clic en el menú raíz **Mantención Barca**, debe abrirse **Calendario Mantenimiento** mediante `action_barca_maintenance_calendar`.
- Los menús principales bajo **Mantención Barca** deben quedar en este orden:
  1. **Mantenimiento**
  2. **Equipos**
  3. **Informes**
  4. **Configuración**
- Dentro del menú principal **Mantenimiento**, los submenús deben quedar en este orden:
  1. **Planes de Mantenimiento**
  2. **Solicitud de Mantención**
  3. **Avisos**
  4. **Orden de Trabajo**
  5. **Calendario Mantenimiento**
- **Avisos** no debe quedar como menú principal; debe depender de `menu_barca_maintenance`.
- La antigua opción basada en `maintenance.request` conserva los XML IDs existentes (`action_barca_maintenance_report`, `menu_barca_reporting_requests`) y se muestra visualmente como **Orden de Trabajo**. No renombrar su modelo técnico ni romper referencias existentes.
- **Solicitud de Mantención** es el requerimiento simple inicial (`barca.maintenance.request`), no la OT estándar. Debe ubicarse antes de **Avisos** y puede generar un `barca.maintenance.alert` con origen `request`.
- En **Solicitud de Mantención**, la fecha es la fecha actual y queda bloqueada; el equipo de mantenimiento queda bloqueado y se carga automáticamente desde el vehículo; existen los campos **Planta y Lugar detallado** y **Estado del vehículo** (`operativo` / `no_operativo`).
- El menú de equipos debe mostrarse como **Equipos** en plural.

## Convenciones de cambios
- Mantener los XML IDs existentes cuando se reorganicen menús para no romper actualizaciones de instalaciones existentes.
- Validar XML después de editar vistas o menús.
- Revisar que no se introduzcan XML IDs duplicados en `views/*.xml`.
- Si se documenta una decisión funcional del módulo, actualizar también los documentos relevantes en `docs_codex/`.
