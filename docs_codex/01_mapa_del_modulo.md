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
│   └── technical_locations.csv
├── models/
│   ├── __init__.py
│   ├── fleet_vehicle.py
│   ├── fleet_vehicle_log_services.py
│   ├── intervention_type.py
│   ├── maintenance_activity.py
│   ├── maintenance_alert.py
│   ├── maintenance_equipment.py
│   ├── maintenance_kit.py
│   ├── maintenance_plan.py
│   ├── maintenance_plan_line.py
│   ├── maintenance_request.py
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
    ├── maintenance_kit_views.xml
    ├── maintenance_plan_views.xml
    ├── maintenance_request_views.xml
    └── technical_location_views.xml
```

## Carga del módulo

`__manifest__.py` carga en este orden:

1. `security/res_groups.xml`
2. `security/ir.model.access.csv`
3. Secuencia de avisos.
4. Vistas de catálogos y procesos.
5. Vistas base y menús.
6. Vistas de avisos.
7. Vista extendida de flota.
8. Cron vacío histórico.
9. Cron PM real.

Además declara:

```python
'post_init_hook': 'load_technical_locations'
```

Ese hook carga ubicaciones técnicas desde CSV y sincroniza vehículos existentes con `maintenance.equipment`.

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
| `barca.maintenance.alert` | `maintenance_alert.py` | Aviso de mantención con workflow propio. |
| `barca.maintenance.alert.line` | `maintenance_alert.py` | Actividades copiadas desde el plan al aviso. |

## Modelos estándar extendidos

| Modelo estándar | Archivo | Extensión |
|---|---|---|
| `fleet.vehicle` | `fleet_vehicle.py` | Campos internos, medidores, documentación, taller; crea/sincroniza `maintenance.equipment`. |
| `fleet.vehicle.log.services` | `fleet_vehicle_log_services.py` | Agrega campo `name` de compatibilidad. |
| `maintenance.equipment` | `maintenance_equipment.py` | Agrega `vehicle_id` único. |
| `maintenance.request` | `maintenance_request.py` | Al cerrarse una OT asociada, mueve aviso en proceso a revisión. |

## Menú principal

El menú raíz es `Mantención Barca` (`menu_barca_maintenance_root`).

Submenús principales:

- `Mantenimiento`
  - `Planes de Mantenimiento`
  - `Avisos`
  - `Solicitudes de Mantenimiento`
  - `Calendario Mantenimiento`
- `Equipos`
- `Informes`
- `Configuración`
  - `Ubicaciones técnicas`
  - `Tipos de intervención`
  - `Actividades`
  - `Kits`
  - `Categorías de equipos`
  - `Equipos de mantenimiento`

## Cron

`data/cron_pm_alerts.xml` crea `ir_cron_generate_pm_alerts`:

```python
model.run_pm_scheduler()
```

Se ejecuta diariamente y evalúa planes activos para generar avisos PM.
