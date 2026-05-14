# 01 — Mapa del módulo

## Estructura actual

```text
zmm_ajustes/
├── __init__.py
├── __manifest__.py
├── hooks.py
├── data/
│   ├── cron.xml
│   ├── cron_pm_alerts.xml
│   ├── maintenance_alert_sequence.xml
│   ├── maintenance_checklist_items.xml
│   └── maintenance_checklist_sequence.xml
├── models/
│   ├── __init__.py
│   ├── fleet_vehicle.py
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
3. Secuencias de avisos, solicitudes simples y checklists.
4. Datos/catálogo de checklist y vistas de catálogos/procesos.
5. Vistas base y menús raíz.
6. Vistas y menú de solicitud simple.
7. Vistas y menú de Checklist.
8. Vistas de avisos.
9. Vista extendida de flota.
10. Cron vacío histórico.
11. Cron PM real.

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

## Modelos estándar extendidos

| Modelo estándar | Archivo | Extensión |
|---|---|---|
| `fleet.vehicle` | `fleet_vehicle.py` | Campos internos, medidores, documentación, taller; crea/sincroniza `maintenance.equipment`. |
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
  - `Checklist`

## Cron

`data/cron_pm_alerts.xml` crea `ir_cron_generate_pm_alerts`:

```python
model.run_pm_scheduler()
```

Se ejecuta diariamente y evalúa planes activos para generar avisos PM.
