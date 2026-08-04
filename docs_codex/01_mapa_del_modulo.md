# 01 — Mapa del módulo

## Estructura actual

```text
zmm_ajustes/
├── __init__.py
├── __manifest__.py
├── hooks.py
├── controllers/
│   ├── __init__.py
│   ├── checklist.py
│   └── maintenance_request_website.py
├── data/
│   ├── checklist_offline_form.xml
│   ├── cron.xml
│   ├── cron_fleet_expiration_alerts.xml
│   ├── cron_pm_alerts.xml
│   ├── fleet_alert_rule_data.xml
│   ├── maintenance_alert_sequence.xml
│   ├── maintenance_checklist_items.xml
│   ├── maintenance_checklist_sequence.xml
│   ├── maintenance_request_offline_form.xml
│   ├── maintenance_request_simple_sequence.xml
│   ├── maintenance_workorder_sequence.xml
│   └── maintenance_stage_data.xml
├── models/
│   ├── __init__.py
│   ├── fleet_alert_rule.py
│   ├── fleet_vehicle.py
│   ├── fleet_vehicle_log_contract.py
│   ├── fleet_vehicle_log_services.py
│   ├── intervention_type.py
│   ├── maintenance_activity.py
│   ├── maintenance_alert.py
│   ├── maintenance_checklist.py
│   ├── maintenance_equipment.py
│   ├── maintenance_kit.py
│   ├── maintenance_plan.py
│   ├── maintenance_plan_line.py
│   ├── maintenance_request.py
│   ├── maintenance_request_simple.py
│   └── technical_location.py
├── security/
│   ├── ir.model.access.csv
│   ├── record_rules.xml
│   └── res_groups.xml
├── static/src/js/
│   └── workorder_activity_start_button.js
├── templates/
│   ├── checklist_website.xml
│   └── maintenance_request_website.xml
└── views/
    ├── base_views.xml
    ├── fleet_alert_rule_views.xml
    ├── fleet_vehicle_log_contract_views.xml
    ├── fleet_vehicle_views.xml
    ├── intervention_type_views.xml
    ├── maintenance_activity_views.xml
    ├── maintenance_alert_views.xml
    ├── maintenance_checklist_views.xml
    ├── maintenance_kit_views.xml
    ├── maintenance_plan_views.xml
    ├── maintenance_request_views.xml
    ├── maintenance_request_simple_views.xml
    └── technical_location_views.xml
```

## Carga del módulo

`__manifest__.py` carga en este orden:

1. `security/res_groups.xml`
2. `security/record_rules.xml`
3. `security/ir.model.access.csv`
4. Reglas de alertas de flotilla por defecto (`Modificaciones` y `Vencimientos`).
5. Cron de vencimientos de flotilla.
6. Secuencias independientes de avisos (`AVS-*`), órdenes de trabajo (`OT-*`), solicitudes simples (`SM-*`) y checklists.
7. Formularios offline, catálogo de checklist y etapas de OT.
8. Vistas de catálogos y procesos, vistas base y menús.
9. Vistas extendidas de Flotilla y contratos.
10. Cron histórico y cron PM real.
11. Plantillas web de Checklist y Solicitud de Mantención.

El manifiesto también incorpora el asset backend `static/src/js/workorder_activity_start_button.js`.

Además declara:

```python
'post_init_hook': 'sync_existing_vehicle_equipment'
```

Ese hook solo sincroniza vehículos existentes con `maintenance.equipment`. Las ubicaciones técnicas se crean o importan manualmente después de instalar el módulo.

## Modelos propios

| Modelo | Archivo | Rol |
|---|---|---|
| `barca.technical.location` | `technical_location.py` | Árbol de ubicaciones técnicas por categoría de vehículo. |
| `barca.intervention.type` | `intervention_type.py` | Catálogo simple de tipos de intervención. |
| `barca.maintenance.activity` | `maintenance_activity.py` | Actividades de mantención por categoría y ubicación técnica. |
| `barca.maintenance.activity.material` | `maintenance_activity.py` | Propuesta maestra de productos/repuestos/kits (`product.product`) por actividad. |
| `barca.maintenance.plan` | `maintenance_plan.py` | Plan preventivo con triggers por km, días y horas. |
| `barca.maintenance.plan.line` | `maintenance_plan_line.py` | Líneas de actividades del plan. |
| `barca.maintenance.plan.line.material` | `maintenance_plan_line.py` | Productos/repuestos/kits íntegros (`product.product`) asociados a cada actividad del plan. |
| `barca.maintenance.kit` | `maintenance_kit.py` | Kit sugerido legado de materiales/repuestos. |
| `barca.maintenance.kit.line` | `maintenance_kit.py` | Productos y cantidades del kit. |
| `barca.maintenance.request` | `maintenance_request_simple.py` | Solicitud simple de mantención creada por usuarios y fuente opcional de avisos. |
| `barca.maintenance.checklist` | `maintenance_checklist.py` | Checklist operativo por tipo de vehículo; genera aviso automáticamente al guardar si existe al menos un No. |
| `barca.maintenance.checklist.line` | `maintenance_checklist.py` | Puntos de control respondidos Sí/No en cada checklist. |
| `barca.maintenance.checklist.item` | `maintenance_checklist.py` | Catálogo de puntos de control por tipo de vehículo, tipo de control e ítem. |
| `barca.maintenance.alert` | `maintenance_alert.py` | Aviso de mantención con workflow propio. |
| `barca.maintenance.alert.line` | `maintenance_alert.py` | Actividades copiadas desde el plan al aviso. |
| `barca.maintenance.alert.line.material` | `maintenance_alert.py` | Materiales asociados a cada actividad del aviso. |
| `barca.maintenance.workorder.line` | `maintenance_request.py` | Actividades ejecutables de la OT. |
| `barca.maintenance.workorder.line.material` | `maintenance_request.py` | Materiales operativos de cada actividad de OT. |
| `barca.fleet.alert.rule` | `fleet_alert_rule.py` | Listas de distribución por regla para alertas de flotilla. |

## Modelos estándar extendidos

| Modelo estándar | Archivo | Extensión |
|---|---|---|
| `fleet.vehicle` | `fleet_vehicle.py` | Campos internos, medidores, documentación, taller, detección de seguro y licencia; crea/sincroniza `maintenance.equipment` y notifica cambios documentales/vencimientos. |
| `fleet.vehicle.log.contract` | `fleet_vehicle_log_contract.py` | Agrega adjuntos múltiples a contratos de flotilla. |
| `fleet.vehicle.log.services` | `fleet_vehicle_log_services.py` | Agrega campo `name` de compatibilidad. |
| `maintenance.equipment` | `maintenance_equipment.py` | Agrega `vehicle_id` único, contadores relacionados para **Contadores** y documentación relacionada de Flotilla en solo lectura para la pestaña **Documentación** de Equipos. |
| `maintenance.request` | `maintenance_request.py` | Orden de Trabajo operativa: actividades, materiales, revisión/cierre, ingreso/salida de taller y tiempo fuera de servicio. |

## Controladores y formularios web/offline

| Formulario | Controlador | Rutas base | Propiedad |
|---|---|---|---|
| Solicitud de Mantención | `controllers/maintenance_request_website.py` | `/solicitud-mantencion` | Usuario Odoo por `requested_by_id`; token por `external_token_user_id`. |
| Checklist | `controllers/checklist.py` | `/checklist` | Usuario Odoo por `requested_by_id`; token por `external_token_user_id`. |

Ambos controladores pueden mostrar todos los vehículos/equipos disponibles al crear, pero sus listados, detalles y búsquedas idempotentes por UUID se restringen al propietario autenticado.

## Menú principal

El menú raíz es `Mantención Barca` (`menu_barca_maintenance_root`).

Submenús principales:

- `Orígenes Avisos`
  - `Planes de Mantenimiento`
  - `Solicitud de Mantención`
  - `Checklist`
- `Mantenimiento`
  - `Odómetros`
  - `Avisos`
  - `Orden de Trabajo`
  - `Calendario Mantenimiento`
- `Informes`
  - `Solicitudes de mantenimiento`
- `Equipos`
- `Configuración`
  - `Ubicaciones técnicas`
  - `Tipos de intervención`
  - `Actividades`
  - `Kits`
  - `Categorías de equipos`
  - `Equipos de mantenimiento`
  - `Alertas` (también disponible en la configuración del módulo Flotilla)
  - `Checklist`

## Cron

`data/cron_fleet_expiration_alerts.xml` crea `ir_cron_send_fleet_expiration_alerts`, programado diariamente a las 08:00, para enviar la nómina de vencimientos a la regla `Vencimientos`.

`data/cron_pm_alerts.xml` crea `ir_cron_generate_pm_alerts`:

```python
model.run_pm_scheduler()
```

Se ejecuta diariamente y evalúa planes activos para generar avisos PM.
