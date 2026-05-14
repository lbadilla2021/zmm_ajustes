# 01 — Mapa del módulo

## Estructura actual

```text
zmm_ajustes/
├── __init__.py
├── __manifest__.py
├── hooks.py
├── data/
│   ├── cron.xml
│   ├── cron_fleet_expiration_alerts.xml
│   ├── cron_pm_alerts.xml
│   ├── maintenance_alert_sequence.xml
│   ├── maintenance_checklist_items.xml
│   └── maintenance_checklist_sequence.xml
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
│   └── res_groups.xml
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
2. `security/ir.model.access.csv`
3. Reglas de alertas de flotilla por defecto (`Modificaciones` y `Vencimientos`).
4. Secuencias de avisos, solicitudes simples y checklists.
5. Datos/catálogo de checklist y vistas de catálogos/procesos.
6. Vistas base y menús raíz.
7. Vistas de alertas de flotilla.
8. Vistas y menú de solicitud simple.
9. Vistas y menú de Checklist.
10. Vistas de avisos.
11. Vista extendida de flota/contratos.
12. Cron de vencimientos de flotilla.
13. Cron vacío histórico.
14. Cron PM real.

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
| `barca.maintenance.plan` | `maintenance_plan.py` | Plan preventivo con triggers por km, días y horas. |
| `barca.maintenance.plan.line` | `maintenance_plan_line.py` | Líneas de actividades del plan. |
| `barca.maintenance.kit` | `maintenance_kit.py` | Kit sugerido de materiales/repuestos. |
| `barca.maintenance.kit.line` | `maintenance_kit.py` | Productos y cantidades del kit. |
| `barca.maintenance.request` | `maintenance_request_simple.py` | Solicitud simple de mantención creada por usuarios y fuente opcional de avisos. |
| `barca.maintenance.checklist` | `maintenance_checklist.py` | Checklist operativo por tipo de vehículo; genera aviso automáticamente al guardar si existe al menos un No. |
| `barca.maintenance.checklist.line` | `maintenance_checklist.py` | Puntos de control respondidos Sí/No en cada checklist. |
| `barca.maintenance.checklist.item` | `maintenance_checklist.py` | Catálogo de puntos de control por tipo de vehículo, tipo de control e ítem. |
| `barca.maintenance.alert` | `maintenance_alert.py` | Aviso de mantención con workflow propio. |
| `barca.maintenance.alert.line` | `maintenance_alert.py` | Actividades copiadas desde el plan al aviso. |
| `barca.fleet.alert.rule` | `fleet_alert_rule.py` | Listas de distribución por regla para alertas de flotilla. |

## Modelos estándar extendidos

| Modelo estándar | Archivo | Extensión |
|---|---|---|
| `fleet.vehicle` | `fleet_vehicle.py` | Campos internos, medidores, documentación, taller, detección de seguro y licencia; crea/sincroniza `maintenance.equipment` y notifica cambios documentales/vencimientos. |
| `fleet.vehicle.log.contract` | `fleet_vehicle_log_contract.py` | Agrega adjuntos múltiples a contratos de flotilla. |
| `fleet.vehicle.log.services` | `fleet_vehicle_log_services.py` | Agrega campo `name` de compatibilidad. |
| `maintenance.equipment` | `maintenance_equipment.py` | Agrega `vehicle_id` único. |
| `maintenance.request` | `maintenance_request.py` | Modelo estándar mantenido como Orden de Trabajo operativa. |

## Menú principal

El menú raíz es `Mantención Barca` (`menu_barca_maintenance_root`).

Submenús principales:

- `Orígenes Avisos`
  - `Planes de Mantenimiento`
  - `Solicitud de Mantención`
  - `Checklist`
- `Mantenimiento`
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
