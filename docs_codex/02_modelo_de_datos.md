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
barca.maintenance.checklist ──puede originar──> barca.maintenance.alert
barca.maintenance.plan ──genera──> barca.maintenance.alert
barca.maintenance.alert ──contiene──> barca.maintenance.alert.line
barca.maintenance.alert ──crea──> maintenance.request
```

## `fleet.vehicle`

Extensión en `models/fleet_vehicle.py`.

Campos agregados:

### Identificación

- `x_internal_code`: calculado automáticamente desde los dos últimos dígitos de la matrícula del vehículo; se muestra como texto no editable.
- `x_engine_code`: número de motor del vehículo.

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
- `x_doc_tag`: booleano para indicar si el vehículo cuenta con TAG.
- `x_alert_days_before`
- `x_driver_license_expiration_date`: fecha de vigencia de licencia de conducir del empleado asociado al conductor del vehículo, tomada desde `hr.employee.driver_license_expiration_date` provisto por `zhr_ajustes`.
- `x_has_insurance_contract`: casilla calculada de solo lectura, marcada si existe al menos un contrato del vehículo cuyo tipo contenga `Seguro`/`seguro`.

### Notas

- `x_maintenance_note`

### Alertas documentales

Al modificar o borrar la tarjeta combustible (`x_doc_fuel_card`) o cambiar el booleano TAG (`x_doc_tag`), se crea/envía un correo a la lista de distribución de la regla `Modificaciones` del modelo `barca.fleet.alert.rule`.

### Alertas de vencimiento

El botón `Enviar Avisos` y el cron `ir_cron_send_fleet_expiration_alerts` aplican el mismo criterio: revisan licencia de conducir, permiso de circulación y revisión técnica, usando `x_alert_days_before` como ventana de alerta por vehículo, y envían la nómina a la regla `Vencimientos`.

### Regla importante

Al crear un vehículo, el módulo crea automáticamente un `maintenance.equipment` asociado. Al cambiar el nombre del vehículo, sincroniza el nombre del equipo asociado.

## `barca.fleet.alert.rule`

Modelo de configuración para listas de distribución de alertas de flotilla.

Campos principales:

- `rule`: regla textual. Por defecto existen `Modificaciones` y `Vencimientos`.
- `email_names`: nombres de correo/distribución, permitiendo más de uno separado por coma, punto y coma, espacio o salto de línea.

## `fleet.vehicle.log.contract`

Extensión del contrato estándar de flotilla.

Agrega:

- `attachment_ids`: adjuntos múltiples del contrato.

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
- `request_date`: fecha actual, bloqueada para edición manual.
- `requested_by_id`
- `vehicle_id`
- `equipment_id`: bloqueado para edición manual, se carga automáticamente desde el vehículo.
- `priority`
- `detailed_location`: Planta y Lugar detallado.
- `vehicle_status`: `operativo`, `no_operativo`.
- `description`
- `state`: `draft` (Nueva), `alert_created`, `cancelled`.
- `alert_id`: aviso generado desde la solicitud.

Una solicitud simple puede generar un `barca.maintenance.alert` con `source_type == 'request'`, `source_reference` igual al número de solicitud y `source_request_id` como vínculo trazable.


## `barca.maintenance.checklist`

Checklist operativo basado funcionalmente en la Solicitud de Mantención simple. Representa una nueva fuente de avisos sin usar ni modificar la OT estándar `maintenance.request`.

Campos principales:

- `name`: secuencia `CHK-00001`.
- `requested_by_id`: usuario solicitante.
- `vehicle_id`: vehículo/equipo operacional evaluado.
- `equipment_id`: equipo de mantenimiento derivado automáticamente desde el vehículo.
- `checklist_date`: fecha actual, bloqueada para edición manual.
- `detailed_location`: Planta y lugar detallado.
- `vehicle_status`: `operativo`, `no_operativo`.
- `fuel_load_time`: hora de carga de combustible.
- `odometer`: odómetro al momento del checklist.
- `observations`: descripción de la falla usada al generar aviso.
- `checklist_type`: `checklist_camion`, `checklist_camion_equipo_ap`, `checklist_camion_equipo_av`, `checklist_vehiculo`.
- `line_ids`: puntos de control generados desde el catálogo por tipo de vehículo.
- `alert_id`: aviso generado desde el checklist.
- `state`: `new`, `notice_created`, `closed_no_notice`, `cancelled`.

Una línea `barca.maintenance.checklist.line` guarda `control_type`, `control_item`, `yes`, `no` y `sequence`. Los booleanos `yes` y `no` son excluyentes por onchange, normalización en `create()`/`write()` y constraint.

El catálogo `barca.maintenance.checklist.item` almacena los puntos de control por `checklist_type`, `control_type`, `control_item` y `sequence`. El archivo Excel original de ítems no está versionado en el repositorio; `data/maintenance_checklist_items.xml` queda como punto estable de carga mediante XML IDs para incorporar esas filas sin depender del `.xlsx` en runtime.

## `barca.maintenance.alert`

Aviso de mantención.

Campos principales:

- `name`: secuencia `AVS-00001`.
- `description`
- `origin_note`
- `source_type`: `pm`, `checklist`, `request`.
- `source_reference`
- `source_request_id`
- `checklist_id`
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
