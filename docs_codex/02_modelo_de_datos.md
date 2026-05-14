# 02 — Modelo de datos

## Visión general

El modelo central se puede leer así:

```text
fleet.vehicle.model.category
        │
        ├── barca.technical.location
        │         └── barca.maintenance.activity
        │
        ├── barca.maintenance.plan
        │         └── barca.maintenance.plan.line
        │                  ├── barca.technical.location
        │                  ├── barca.maintenance.activity
        │                  └── barca.intervention.type
        │
        └── fleet.vehicle
                  └── maintenance.equipment

barca.maintenance.request ──puede originar──> barca.maintenance.alert
barca.maintenance.plan ──genera──> barca.maintenance.alert
barca.maintenance.alert ──contiene──> barca.maintenance.alert.line
barca.maintenance.alert ──crea──> maintenance.request
```

## `fleet.vehicle`

Extensión en `models/fleet_vehicle.py`.

Campos agregados:

### Identificación

- `x_internal_code`
- `x_engine_code`

### Medición

- `x_odometer_last_service`
- `x_odometer_next_service`, calculado como último servicio + 5000.
- `x_operating_hours`
- `x_hours_last_service`

### Taller

- `x_last_entry_date`
- `x_last_exit_date`
- `x_downtime_total`, actualmente queda en `0.0`.

### Documentación

- `x_doc_circulation_permit_expiry`
- `x_doc_technical_review_expiry`
- `x_doc_padron`
- `x_doc_fuel_card`
- `x_doc_tag`
- `x_alert_days_before`

### Notas

- `x_maintenance_note`

### Regla importante

Al crear un vehículo, el módulo crea automáticamente un `maintenance.equipment` asociado. Al cambiar el nombre del vehículo, sincroniza el nombre del equipo asociado.

## `maintenance.equipment`

Extensión en `models/maintenance_equipment.py`.

Agrega:

- `vehicle_id`: Many2one hacia `fleet.vehicle`, con `ondelete='cascade'`.

Restricción SQL:

```python
unique(vehicle_id)
```

Esto fuerza una relación 1:1 entre vehículo y equipo de mantenimiento.

## `barca.technical.location`

Modelo de ubicaciones técnicas jerárquicas.

Campos principales:

- `name`
- `code`
- `category_id`
- `company_id`
- `parent_id`
- `parent_code`
- `child_ids`
- `complete_name`
- `parent_path`
- `level`
- `kit_id`
- `estimated_useful_life`
- `reference_supplier_id`
- `note`

Características:

- Usa `_parent_name = 'parent_id'`.
- Usa `_parent_store = True`.
- Calcula `complete_name` como ruta jerárquica.
- Calcula `level` según padre.
- Permite asignar padre mediante `parent_code`.
- Crea XML IDs estables mediante `_ensure_external_ids()` usando el `code`.

Restricción SQL:

```python
unique(name, category_id, parent_id)
```

No puede existir la misma ubicación con igual nombre en el mismo nivel y categoría.

## `barca.intervention.type`

Catálogo simple.

Campos:

- `name`
- `code`
- `active`

Sirve para clasificar las líneas de plan y aviso.

## `barca.maintenance.activity`

Actividad de mantención por categoría y ubicación técnica.

Campos:

- `name`
- `code`
- `active`
- `category_id`
- `technical_location_id`
- `technical_location_code`
- `estimated_duration`
- `note`

Restricción SQL:

```python
unique(name, category_id, technical_location_id)
```

Constraint Python:

- La categoría de la ubicación técnica debe coincidir con la categoría de la actividad.

## `barca.maintenance.plan`

Modelo central de planes preventivos.

Campos principales:

- `name`
- `category_id`
- `vehicle_ids`
- `company_id`
- `plan_line_ids`
- `trigger_km`
- `trigger_days`
- `trigger_hours`
- `trigger_km_start`
- `trigger_days_start`
- `trigger_hours_start`
- `advance_km`
- `advance_days`
- `kit_id`
- `active`
- `line_count`

Restricción SQL:

```python
unique(name, category_id)
```

Constraints Python:

- Debe tener categoría o vehículos específicos.
- Debe tener al menos un trigger: km, días u horas.
- Los triggers deben ser mayores a cero si se informan.
- `advance_km` debe ser menor que `trigger_km`.
- `advance_days` debe ser menor que `trigger_days`.

## `barca.maintenance.plan.line`

Línea de actividad de un plan.

Campos:

- `sequence`
- `plan_id`
- `category_id`, relacionado desde el plan.
- `technical_location_id`
- `intervention_type_id`
- `activity_id`
- `estimated_duration`
- `note`

Reglas:

- `activity_id` debe corresponder a la ubicación técnica.
- `activity_id` debe corresponder a la categoría del plan.
- Al cambiar ubicación técnica, limpia actividad incompatible.
- Al elegir actividad, copia duración estimada si la línea no tiene duración propia.


## `barca.maintenance.request`

Solicitud simple de mantención. Representa el requerimiento inicial generado por un usuario, supervisor u otro solicitante antes de la evaluación técnica.

Campos principales:

- `name`: secuencia `SM-00001`.
- `request_date`
- `requested_by_id`
- `vehicle_id`
- `equipment_id`
- `priority`
- `description`
- `state`: `draft` (Nueva), `alert_created`, `cancelled`.
- `alert_id`: aviso generado desde la solicitud.

Una solicitud simple puede generar un `barca.maintenance.alert` con `source_type == 'request'`, `source_reference` igual al número de solicitud y `source_request_id` como vínculo trazable.

## `barca.maintenance.alert`

Aviso de mantención.

Campos principales:

- `name`: secuencia `AVS-00001`.
- `description`
- `origin_note`
- `source_type`: `pm`, `checklist`, `request`.
- `source_reference`
- `source_request_id`
- `pm_id`
- `vehicle_id`
- `equipment_id`
- `alert_line_ids`
- `priority`: `low`, `medium`, `high`.
- `state`
- `odometer`
- `operating_hours`
- `alert_date`
- `evaluation_date`
- `review_date`
- `close_date`
- `evaluated_by_id`
- `approved_by_id`
- `closed_by_id`
- `maintenance_request_id`

Hereda:

```python
['mail.thread', 'mail.activity.mixin']
```

Por lo tanto tiene chatter y actividades.

## `barca.maintenance.alert.line`

Línea de actividad del aviso.

Campos:

- `sequence`
- `alert_id`
- `plan_line_id`
- `technical_location_id`
- `intervention_type_id`
- `activity_id`
- `estimated_duration`
- `done`
- `note`

Estas líneas se copian desde `barca.maintenance.plan.line` al crear aviso desde PM.

## `barca.maintenance.kit`

Kit de materiales/repuestos.

Campos:

- `name`
- `code`
- `category_id`
- `technical_location_id`
- `line_ids`
- `active`
- `note`

Restricción SQL:

```python
unique(code)
```

Constraint:

- La categoría de la ubicación técnica debe coincidir con la categoría del kit.

## `barca.maintenance.kit.line`

Línea de kit.

Campos:

- `kit_id`
- `product_id`
- `quantity`
- `uom_id`
- `note`

Constraint:

- `quantity` debe ser mayor a cero.

## `maintenance.request`

Extensión en `models/maintenance_request.py`.

La Solicitud de Mantención estándar de Odoo se renombra funcionalmente como Orden de Trabajo. Su ciclo de programación, ejecución, revisión y cierre queda separado del ciclo del aviso `barca.maintenance.alert`.

El aviso asociado queda en estado técnico `in_progress` / funcional `Con OT creada` hasta que el usuario lo cierre explícitamente. El cierre del aviso solo se permite si la OT asociada está en una etapa terminada (`stage_id.done`), equivalente funcionalmente a Reparado o Desechar.
