# Menús de Mantención Barca

## Comportamiento de apertura

Al abrir el módulo **Mantención Barca** desde el selector de aplicaciones de Odoo, o al hacer clic en el menú raíz **Mantención Barca** dentro del módulo, debe abrirse la acción **Calendario Mantenimiento**.

- XML ID del menú raíz: `menu_barca_maintenance_root`
- Acción por defecto: `action_barca_maintenance_calendar`
- Archivo principal: `views/base_views.xml`

## Menús principales

Bajo el menú raíz **Mantención Barca**, el orden vigente de menús principales es:

| Secuencia | Menú | XML ID | Acción |
| --- | --- | --- | --- |
| 10 | Mantenimiento | `menu_barca_maintenance` | Sin acción directa |
| 20 | Equipos | `menu_barca_equipment` | `action_barca_equipment` |
| 30 | Informes | `menu_barca_reporting` | Sin acción directa |
| 40 | Configuración | `menu_barca_configuraciones` | Sin acción directa |

## Submenús de Mantenimiento

Dentro del menú principal **Mantenimiento**, el orden vigente es:

| Secuencia | Submenú | XML ID | Acción | Archivo |
| --- | --- | --- | --- | --- |
| 10 | Planes de Mantenimiento | `menu_barca_maintenance_plan` | `action_barca_maintenance_plan` | `views/base_views.xml` / `views/maintenance_plan_views.xml` |
| 15 | Solicitud de Mantención | `menu_barca_maintenance_simple_request` | `action_barca_maintenance_simple_request` | `views/maintenance_request_simple_views.xml` |
| 20 | Avisos | `menu_barca_maintenance_alert` | `action_barca_maintenance_alert` | `views/maintenance_alert_views.xml` |
| 30 | Orden de Trabajo | `menu_barca_reporting_requests` | `action_barca_maintenance_report` | `views/base_views.xml` |
| 40 | Calendario Mantenimiento | `menu_barca_reporting_calendar` | `action_barca_maintenance_calendar` | `views/base_views.xml` |

## Reglas funcionales que no se deben perder

- **Avisos** debe estar dentro de **Mantenimiento** y no como menú principal.
- La **Solicitud de Mantención** simple es el requerimiento inicial de usuario y debe ubicarse antes de **Avisos**.
- La antigua opción basada en `maintenance.request` conserva su XML ID y modelo técnico, pero se muestra como **Orden de Trabajo**.
- **Planes de Mantenimiento** debe estar dentro de **Mantenimiento** como primer submenú.
- **Calendario Mantenimiento** debe mantenerse dentro de **Mantenimiento** y además como acción por defecto del menú raíz.
- El menú principal de equipos debe llamarse **Equipos**.
- Mantener los XML IDs existentes ayuda a que las actualizaciones del módulo no creen menús duplicados ni pierdan referencias existentes.

## Validaciones recomendadas

Después de cambiar menús o vistas XML, ejecutar una validación de parseo XML y una revisión de IDs duplicados en `views/*.xml`.
