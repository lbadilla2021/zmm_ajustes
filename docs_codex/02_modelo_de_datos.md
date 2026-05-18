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
barca.maintenance.alert.line ──contiene──> barca.maintenance.alert.line.material
barca.maintenance.alert ──crea──> maintenance.request
maintenance.request ──contiene──> barca.maintenance.workorder.line
barca.maintenance.workorder.line ──contiene──> barca.maintenance.workorder.line.material
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
- `x_alert_days_before`: ventana de días por vehículo para considerar próximos vencimientos documentales. Si viene negativo, la lógica lo trata como `0`.
- `x_driver_license_expiration_date`: fecha de vigencia de licencia de conducir del empleado asociado al conductor del vehículo, tomada desde `hr.employee.driver_license_expiration_date` provisto por `zhr_ajustes`. La búsqueda del empleado usa `work_contact_id` y/o `address_home_id` según existan en la base.
- `x_has_insurance_contract`: casilla calculada de solo lectura, marcada si existe al menos un contrato activo o inactivo del vehículo cuyo subtipo de costo contenga `seguro`.

### Notas

- `x_maintenance_note`

### Alertas documentales

Al modificar o borrar la tarjeta combustible (`x_doc_fuel_card`) o cambiar el booleano TAG (`x_doc_tag`), se crea/envía un correo a la lista de distribución de la regla `Modificaciones` del modelo `barca.fleet.alert.rule`. El correo resume cambios por vehículo en formato valor anterior → valor nuevo. Si la regla no tiene destinatarios, no se envía correo.

### Alertas de vencimiento

El botón `Enviar Avisos` y el cron `ir_cron_send_fleet_expiration_alerts` aplican el mismo criterio: revisan licencia de conducir, permiso de circulación y revisión técnica, usando `x_alert_days_before` como ventana de alerta por vehículo, y envían la nómina a la regla `Vencimientos`. La revisión siempre se ejecuta sobre todos los vehículos, no solo sobre el registro abierto desde el botón. Si no hay vencimientos próximos o no hay destinatarios, el botón muestra una notificación de advertencia.

### Vista de Flotilla

`views/fleet_vehicle_views.xml` hereda `fleet.fleet_vehicle_view_form` y `hr_fleet.fleet_vehicle_view_form_inherit_hr`. En el formulario de vehículo:

- Muestra `x_internal_code` bajo la patente.
- Muestra `x_driver_license_expiration_date` después del conductor.
- Oculta `future_driver_id`, `plan_to_change_car`, `order_date`, `manager_id` y `mobility_card`.
- Reubica `location` después de `next_assignation_date`.
- Muestra `x_operating_hours` junto al bloque de odómetro.
- Muestra `x_engine_code` y `x_has_insurance_contract` después del VIN.
- Reemplaza la pestaña fiscal estándar por **Documentación**.
- Agrega la pestaña **Taller** con último servicio, horas último servicio y fechas de entrada/salida a taller, todos visibles en solo lectura para usuarios de Flotilla.

### Regla importante

Al crear un vehículo, el módulo crea automáticamente un `maintenance.equipment` asociado. Al cambiar el nombre del vehículo, sincroniza el nombre del equipo asociado.

## `barca.fleet.alert.rule`

Modelo de configuración para listas de distribución de alertas de flotilla.

Campos principales:

- `rule`: regla textual. Por defecto existen `Modificaciones` y `Vencimientos`; `data/fleet_alert_rule_data.xml` ejecuta `_ensure_default_rules()` para asegurar ambas.
- `email_names`: correos/listas de distribución, permitiendo más de uno separado por coma, punto y coma, espacio o salto de línea.

Reglas productivas vigentes:

- `Modificaciones`: destinatarios de cambios en tarjeta combustible y TAG.
- `Vencimientos`: destinatarios de licencias, permisos de circulación y revisiones técnicas por vencer.

## `fleet.vehicle.log.contract`

Extensión del contrato estándar de flotilla.

Agrega:

- `attachment_ids`: adjuntos múltiples del contrato, expuestos en la vista de contrato después del campo de notas con widget `many2many_binary`.

## `fleet.vehicle.log.services`

Extensión mínima del historial estándar de servicios de flotilla.

Agrega:

- `name`: campo `Char` de compatibilidad para vistas de búsqueda o componentes que esperan un campo técnico `name` en `fleet.vehicle.log.services`.

## `maintenance.equipment`

Extensión en `models/maintenance_equipment.py`.

Agrega:

- `vehicle_id`: Many2one hacia `fleet.vehicle`, con `ondelete='cascade'`.
- `x_odometer_last_service`: odómetro del último servicio del vehículo, relacionado y solo lectura.
- `x_hours_last_service`: horas de operación del último servicio del vehículo, relacionado y solo lectura.
- `x_last_entry_date`: última entrada a taller del vehículo, relacionada y solo lectura.
- `x_last_exit_date`: última salida a taller del vehículo, relacionada y solo lectura.
- `x_current_odometer`: último odómetro actual del vehículo, relacionado y solo lectura.
- `x_current_operating_hours`: horas de operación actuales del vehículo, relacionadas y solo lectura.

La vista de equipos agrega una pestaña **Contadores** con dos bloques: **Taller** para los cuatro contadores históricos de taller y **Actual** para odómetro y horas de operación vigentes.

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
- `material_template_line_ids`: propuesta maestra de materiales, repuestos o kits para nuevos planes.
- `material_count`: contador visible de materiales propuestos.
- `material_summary`: resumen visible de materiales propuestos.

Restricción SQL:

```python
unique(name, category_id, technical_location_id)
```

Constraint Python:

- La categoría de la ubicación técnica debe coincidir con la categoría de la actividad.

## `barca.maintenance.activity.material`

Línea maestra de material, repuesto o kit propuesto para una actividad de mantención. Sirve como plantilla para nuevas líneas de plan; al seleccionarse la actividad en un plan, sus materiales se copian a `barca.maintenance.plan.line.material`.

Campos:

- `sequence`
- `activity_id`
- `product_id`: producto de Odoo (`product.product`), mostrado como **Repuesto / Kit / Material**.
- `product_uom_id`
- `quantity`
- `note`

Reglas:

- Al seleccionar `product_id`, se propone `product_uom_id` desde la unidad de medida del producto.
- `quantity` debe ser mayor que cero.
- `product_id` es obligatorio.
- Estos registros son la propuesta maestra; editar materiales copiados en un plan no modifica la actividad maestra.

## `barca.maintenance.plan`

Modelo central de planes preventivos.

Campos principales:

- `name`
- `category_id`
- `vehicle_ids`
- `company_id`
- `plan_line_ids`
- `material_line_ids`: vista plana de materiales/repuestos/kits del plan agrupables por actividad.
- `trigger_km`
- `trigger_days`
- `trigger_hours`
- `trigger_km_start`
- `trigger_days_start`
- `trigger_hours_start`
- `advance_km`
- `advance_days`
- `kit_id`: campo legado de kit sugerido en encabezado, mantenido por compatibilidad. No es el mecanismo principal de planificación de materiales.
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
- `material_line_ids`: materiales, repuestos o kits asociados directamente a la actividad.
- `material_count`: contador visible de materiales asociados.
- `material_summary`: resumen visible con hasta tres productos y sufijo `(+N)` si existen más.

Reglas:

- `activity_id` debe corresponder a la ubicación técnica.
- `activity_id` debe corresponder a la categoría del plan.
- Al cambiar ubicación técnica, limpia actividad incompatible.
- Al elegir actividad, copia duración estimada si la línea no tiene duración propia.
- La grilla de actividades del plan muestra `material_count` y `material_summary` para identificar rápidamente si la actividad tiene repuestos, materiales o kits asociados.
- Al seleccionar una actividad con materiales maestros propuestos, se copian como líneas propias del plan si la línea aún no tiene materiales. Desde ese momento pueden modificarse o eliminarse sin afectar el maestro de actividades.

## `barca.maintenance.plan.line.material`

Línea de material, repuesto o kit asociado a una actividad específica del plan (`barca.maintenance.plan.line`).

Campos:

- `sequence`
- `plan_id`: plan al que pertenece el material, usado para editar todos los materiales estructurados desde el formulario del plan.
- `plan_line_id`: actividad específica del plan.
- `product_id`: producto de Odoo (`product.product`), mostrado funcionalmente como **Repuesto / Kit / Material**.
- `product_uom_id`: unidad de medida estimada.
- `quantity`: cantidad estimada.
- `note`

Reglas:

- Al seleccionar `product_id`, se propone `product_uom_id` desde la unidad de medida del producto.
- `quantity` debe ser mayor que cero.
- `product_id` es obligatorio.
- Si se informa `product_uom_id`, debe corresponder a una unidad de medida existente.
- `plan_line_id` debe pertenecer al `plan_id` del material.

Importante: para esta lógica nueva, un kit es un `product.product` íntegro ya existente en el maestro de productos. No se explotan kits en componentes y no se usa `barca.maintenance.kit.line` para los materiales por actividad del plan.


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



## Extensión `maintenance.request`

La OT estándar se extiende para mantener una estructura operativa propia copiada desde el aviso, sin leer materiales en vivo desde el plan ni desde el aviso.

Campos Barca agregados:

- `barca_alert_id`: aviso Barca que originó la OT.
- `barca_activity_line_ids`: actividades ejecutables de la OT (`barca.maintenance.workorder.line`).
- `barca_activity_count`: contador calculado de actividades.

## `barca.maintenance.workorder.line`

Actividad ejecutable dentro de una OT estándar. Se crea al generar la OT desde un aviso y conserva trazabilidad opcional hacia la actividad del aviso.

Campos principales:

- `sequence`
- `maintenance_request_id`
- `alert_line_id`
- `alert_id`: relacionado desde la actividad del aviso.
- `plan_line_id`: relacionado desde la actividad del aviso.
- `technical_location_id`
- `intervention_type_id`
- `activity_id`
- `description`
- `estimated_duration`
- `state`: `pending`, `in_progress`, `notified`, `closed`.
- `note`
- `material_line_ids`: materiales/repuestos/kits ejecutables de la actividad de OT.
- `material_count`: contador de materiales propios de la actividad de OT.
- `material_summary`: resumen de hasta tres productos copiados/agregados en la actividad de OT, con sufijo `(+N)` si existen más.

## `barca.maintenance.workorder.line.material`

Material, repuesto o kit ejecutable asociado a una actividad de OT. Es una copia independiente del material evaluado del aviso; no explota kits y todos los productos son `product.product`. Los cambios posteriores en el aviso no actualizan ni reemplazan estas líneas de OT.

Campos principales:

- `sequence`
- `workorder_line_id`
- `maintenance_request_id`: relacionado desde la actividad de OT.
- `alert_line_material_id`
- `product_id`
- `product_uom_id`
- `product_uom_category_id`
- `estimated_quantity`
- `reserved_quantity`
- `withdrawn_quantity`
- `consumed_quantity`
- `returned_quantity`
- `note`

Reglas:

- Todas las cantidades deben ser mayores o iguales a cero.
- `product_id` y `product_uom_id` son obligatorios.
- La unidad de medida debe ser compatible con la categoría de UdM del producto.
- En esta fase no hay reservas, pickings, compras, consumos reales, devoluciones ni movimientos de inventario.

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
- `material_line_ids`: materiales, repuestos o kits evaluables/editables de esa actividad del aviso.
- `material_count`: contador visible de materiales asociados a la actividad del aviso.
- `material_summary`: resumen visible con hasta tres productos y sufijo `(+N)` si existen más.

Estas líneas se copian desde `barca.maintenance.plan.line` al crear aviso desde PM. Sus materiales se copian desde `barca.maintenance.plan.line.material` hacia líneas nuevas de `barca.maintenance.alert.line.material`, por lo que cada aviso mantiene registros propios e independientes del plan. No existen materiales globales en el encabezado del aviso.

## `barca.maintenance.alert.line.material`

Línea de material, repuesto o kit asociado a una actividad específica del aviso (`barca.maintenance.alert.line`). Es el nivel operativo donde Tomas puede evaluar y ajustar los materiales requeridos para la actividad del aviso.

Campos:

- `sequence`
- `alert_line_id`: actividad específica del aviso.
- `alert_id`: aviso relacionado, calculado desde `alert_line_id` para trazabilidad y búsqueda.
- `plan_line_material_id`: material de línea de plan origen, opcional y conservado solo como referencia.
- `product_id`: producto de Odoo (`product.product`), mostrado como **Repuesto / Kit / Material**.
- `product_uom_id`: unidad de medida estimada.
- `product_uom_category_id`: categoría de UdM del producto para restringir unidades compatibles.
- `estimated_quantity`: cantidad estimada editable en el aviso.
- `available_quantity`: disponible simple calculado desde `product_id.qty_available`; no implementa lógica por bodega.
- `note`

Reglas:

- `estimated_quantity` debe ser mayor que cero.
- `product_id` y `product_uom_id` son obligatorios.
- `product_uom_id` debe pertenecer a la misma categoría que la unidad de medida del producto.
- Los materiales del aviso siempre pertenecen a una línea de actividad; no se agregan materiales al encabezado de `barca.maintenance.alert`.
- Un kit sigue siendo un `product.product` íntegro; no se explota en componentes.

Flujo de materiales:

```text
Actividad maestra (`barca.maintenance.activity`)
  → propone materiales estándar (`barca.maintenance.activity.material`)
Actividad del plan (`barca.maintenance.plan.line`)
  → guarda materiales específicos del plan (`barca.maintenance.plan.line.material`)
Actividad del aviso (`barca.maintenance.alert.line`)
  → guarda materiales evaluables/editables (`barca.maintenance.alert.line.material`)
```

## `barca.maintenance.kit`

Kit de materiales/repuestos legado. Se mantiene por compatibilidad con datos y vistas existentes; la planificación nueva de materiales/repuestos/kits por actividad del plan utiliza `barca.maintenance.plan.line.material` con productos `product.product`.

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

El aviso asociado queda en estado técnico `in_progress` / funcional `Con OT creada` hasta que el usuario lo cierre explícitamente. El cierre del aviso solo se permite si la OT asociada está en una etapa terminada (`stage_id.done`), equivalente funcionalmente a Reparado o Desechar. La descripción de la OT puede guardar un resumen textual de actividades, pero el detalle operativo estable se guarda en `barca_activity_line_ids` y en sus materiales.

### Fase 4: ciclo operativo de actividades de OT

`barca.maintenance.workorder.line` administra el avance operativo básico de cada actividad ejecutable de la OT con el campo `state` y los valores técnicos:

- `pending`: Pendiente.
- `in_progress`: En ejecución.
- `notified`: Notificada.
- `closed`: Cerrada.

Varias actividades de una misma OT pueden estar en `in_progress` al mismo tiempo; el modelo no aplica una restricción de actividad única en ejecución. La notificación de avance se registra en la misma actividad mediante:

- `notification_note`: descripción manual de lo realizado.
- `result`: resultado informado (`resolved`, `partial`, `not_resolved`).
- `notification_date`: fecha/hora asignada automáticamente al notificar.
- `notified_by_id`: usuario que notificó la actividad.

`maintenance.request` calcula contadores de actividades Barca para apoyar revisión operativa:

- `barca_total_activity_count`.
- `barca_notified_activity_count`: considera actividades `notified` y `closed`.
- `barca_closed_activity_count`.
- `barca_all_activities_notified`.
- `barca_all_activities_closed`.

En materiales de OT (`barca.maintenance.workorder.line.material`), Fase 4 mantiene visibles las cantidades operativas manuales `estimated_quantity`, `reserved_quantity`, `withdrawn_quantity`, `consumed_quantity` y `returned_quantity`, junto con producto, UdM y observación, y valida que no sean negativas. El consumo informado (`consumed_quantity`) es un dato manual de avance; no descuenta inventario ni exige haber retirado material desde bodega. Los campos de reserva, retiro, consumo y devolución quedan disponibles para Fase 5 y Fase 6, sin crear `stock.move`, `stock.picking`, reservas, retiros, devoluciones ni compras en esta fase.
