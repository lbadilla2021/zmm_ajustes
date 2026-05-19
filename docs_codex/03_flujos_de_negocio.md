# 03 — Flujos de negocio

## Flujo principal PM

```text
Plan de mantenimiento preventivo
        │
        │ evalúa triggers por km/días/horas
        ▼
Aviso de mantención
        │
        ├── Pendiente evaluación
        ├── Aprobado
        ├── Rechazado
        ├── En proceso
        ├── En revisión
        └── Cerrado
        │
        ▼
Orden de Trabajo / maintenance.request
```

## Creación de planes

Un plan (`barca.maintenance.plan`) puede aplicar por:

1. Categoría de vehículo (`category_id`).
2. Vehículos específicos (`vehicle_ids`).
3. Ambos a la vez.

La función `_get_plan_vehicles()` une los vehículos específicos con los vehículos de la categoría.

El plan debe tener líneas (`plan_line_ids`). Si no tiene líneas, el cron o la acción manual lo omiten. Cada línea de actividad puede tener sus propios materiales, repuestos o kits en `material_line_ids`.


## Materiales, repuestos y kits por actividad

Los materiales de mantenimiento preventivo se definen a nivel de actividad. No se registran materiales en el encabezado del plan ni en el encabezado del aviso.

El diseño vigente separa cuatro niveles:

```text
Actividad maestra
  → propone materiales estándar
Actividad del plan
  → guarda materiales planificados
Actividad del aviso
  → guarda materiales evaluados
Actividad OT
  → guarda materiales ejecutables
```

El maestro de actividades (`barca.maintenance.activity`) puede mantener una propuesta de productos en `material_template_line_ids`. Al seleccionar esa actividad en una línea del plan, la propuesta se copia a materiales propios del plan; luego el plan puede mantener, cambiar, agregar o eliminar materiales sin modificar el maestro.

Cada actividad del plan puede registrar una o más líneas `barca.maintenance.plan.line.material` con:

- Secuencia.
- Producto `product.product`, visible como **Repuesto / Kit / Material**.
- Cantidad estimada.
- Unidad de medida.
- Observación.

En esta implementación, un kit se trata como un producto íntegro del maestro de productos de Odoo (`product.product`). No se explota en componentes y no participa `barca.maintenance.kit.line` en la nueva lógica de materiales por actividad.

El campo `kit_id` del encabezado de `barca.maintenance.plan` queda como campo legado de compatibilidad y ya no es el mecanismo principal para planificar materiales/repuestos/kits.

En el formulario del plan, la grilla principal de actividades muestra **N° materiales** y **Materiales** para que el usuario vea inmediatamente qué actividades tienen productos asociados. Además, la pestaña **Materiales por actividad** permite editar los datos estructurados del plan en una sola grilla: actividad del plan, producto, cantidad, UdM y observación. El resumen lista hasta tres productos y agrega `(+N)` cuando hay más de tres.

Cuando un plan genera un aviso, los materiales de cada actividad del plan se copian a materiales propios de la actividad del aviso (`barca.maintenance.alert.line.material`). La copia mantiene producto, unidad, cantidad estimada, secuencia, nota y referencia al material del plan, pero crea registros nuevos. Por eso, cambiar materiales del plan después no modifica avisos ya generados.

En el aviso, cada actividad muestra **N° materiales** y **Materiales** en la grilla de actividades. Al abrir una actividad del aviso, la pestaña **Materiales / Repuestos / Kits** permite editar producto, cantidad estimada, unidad de medida y observación. El disponible mostrado es una referencia simple tomada desde `product_id.qty_available`; todavía no existe lógica por bodega, reservas, compras, consumos ni movimientos de inventario.

Cuando el aviso genera una OT estándar (`maintenance.request`), las actividades del aviso se copian a `barca.maintenance.workorder.line` y sus materiales/repuestos/kits se copian a `barca.maintenance.workorder.line.material`. La OT no lee materiales en vivo desde el plan ni desde el aviso: mantiene registros propios ejecutables con trazabilidad al aviso. Las cantidades operativas (`reserved_quantity`, `withdrawn_quantity`, `consumed_quantity`, `returned_quantity`) son campos estructurales de la OT para fases futuras; en esta etapa no crean reservas, pickings, compras, consumos, devoluciones ni movimientos de inventario.

## Triggers del plan

El plan puede disparar por cualquiera de estas condiciones:

- Kilómetros.
- Días.
- Horas.

La lógica combinada es OR: basta con que un trigger activo se cumpla para generar aviso.

### Trigger por km

Campos:

- `trigger_km_start`
- `trigger_km`
- `advance_km`

Lecturas del vehículo:

- Km actual: `fleet.vehicle.odometer`.
- Último servicio: `fleet.vehicle.x_odometer_last_service`.

Regla:

```text
si last_service_km > 0:
    next_km = max(trigger_km_start, last_service_km + trigger_km)
si no:
    next_km = trigger_km_start o trigger_km

threshold_km = next_km - advance_km
se dispara si odometer_actual >= threshold_km
```

Importante: si el plan tiene `trigger_km` y el vehículo no tiene km actual, `_create_alert_for_vehicle()` omite ese vehículo.

### Trigger por días

Campos:

- `trigger_days_start`
- `trigger_days`
- `advance_days`

Fecha base:

La función `_get_vehicle_maintenance_base_date()` prioriza:

1. `x_last_entry_date`
2. `x_last_exit_date`
3. `acquisition_date`

Último servicio:

- `x_last_exit_date`

Regla:

```text
start_date = base_date + trigger_days_start
next_date = max(start_date, last_service_date + trigger_days) si hay último servicio
threshold_date = next_date - advance_days
se dispara si today >= threshold_date
```

Si no hay fecha base confiable, conserva comportamiento conservador usando `today + trigger_days_start`.

### Trigger por horas

Campos:

- `trigger_hours_start`
- `trigger_hours`

Lectura de horas actuales:

La función `_get_vehicle_hours()` busca en este orden:

1. `x_operating_hours`
2. `operating_hours`
3. `hours_meter`

Último servicio por horas:

- `x_hours_last_service`

Regla:

```text
si last_service_hours > 0:
    next_hours = max(trigger_hours_start, last_service_hours + trigger_hours)
si no:
    next_hours = trigger_hours_start o trigger_hours

se dispara si current_hours >= next_hours
```

## Generación de avisos

Los avisos se generan desde:

- Botón `Generar avisos` en formulario del plan.
- Cron diario `ir_cron_generate_pm_alerts`.

Métodos clave:

- `action_generate_alerts()`
- `_evaluate_and_generate_alerts()`
- `_create_alert_for_vehicle()`
- `run_pm_scheduler()`

## Flujo de alertas documentales de Flotilla

```text
Cambio en fleet.vehicle.x_doc_fuel_card o x_doc_tag
        │
        ▼
write() captura valores anteriores
        │
        ▼
_send_documentation_change_email() arma resumen por vehículo
        │
        ▼
barca.fleet.alert.rule("Modificaciones") entrega destinatarios
        │
        ▼
mail.mail envía "Modificaciones de documentación de vehículos"
```

Puntos importantes:

- Solo se observan `x_doc_fuel_card` y `x_doc_tag`.
- Si el valor final es igual al inicial, no se reporta cambio.
- Si la regla `Modificaciones` no tiene destinatarios, no se envía correo.

## Flujo de vencimientos de Flotilla

```text
Botón Enviar Avisos o cron ir_cron_send_fleet_expiration_alerts
        │
        ▼
fleet.vehicle._send_expiration_alerts() busca todos los vehículos
        │
        ▼
_get_expiration_alert_items() compara fechas contra hoy + x_alert_days_before
        │
        ▼
barca.fleet.alert.rule("Vencimientos") entrega destinatarios
        │
        ▼
mail.mail envía "Vencimientos de documentación de flotilla"
```

Documentos evaluados:

- Licencia de conducir del conductor (`x_driver_license_expiration_date`).
- Permiso de circulación (`x_doc_circulation_permit_expiry`).
- Revisión técnica (`x_doc_technical_review_expiry`).

Notas operativas:

- La ventana `x_alert_days_before` es individual por vehículo y se normaliza a mínimo `0`.
- El botón del formulario no limita la revisión al vehículo actual; usa todos los vehículos.
- Si no hay vencimientos o destinatarios, el botón muestra advertencia y el cron retorna `0`.

## Flujo de seguro y contratos de Flotilla

La casilla `x_has_insurance_contract` se calcula desde contratos del vehículo, incluyendo registros inactivos (`active_test=False`). Queda marcada cuando existe al menos un `fleet.vehicle.log.contract` relacionado cuyo `cost_subtype_id.name` contiene `seguro`.

Los contratos de flotilla agregan `attachment_ids` para respaldos múltiples, visibles después de notas.

## Prevención de duplicados

Antes de crear un aviso PM, el módulo busca avisos abiertos para el mismo vehículo:

```python
[
    ('source_type', '=', 'pm'),
    ('vehicle_id', '=', vehicle.id),
    ('state', 'not in', ['closed', 'rejected']),
]
```

Consecuencia: un vehículo no puede tener más de un aviso PM abierto, aunque existan varios planes disparados.

El cron ordena planes por:

```python
trigger_km asc, trigger_days asc, trigger_hours asc
```

Esto hace que planes con menor intervalo se evalúen primero. Una vez creado un aviso, los planes siguientes quedan bloqueados por duplicado para ese vehículo.

## Copia de actividades al aviso

Al crear aviso desde plan:

- Crea `barca.maintenance.alert`.
- Copia cada `barca.maintenance.plan.line` a `barca.maintenance.alert.line`.
- Conserva trazabilidad mediante `plan_line_id`.
- Copia cada `barca.maintenance.plan.line.material` de la actividad del plan a una línea nueva `barca.maintenance.alert.line.material` dentro de la actividad del aviso.
- Conserva trazabilidad del material mediante `plan_line_material_id`, sin reutilizar el registro del plan.

Campos copiados:

- `activity_id`
- `technical_location_id`
- `intervention_type_id`
- `estimated_duration`
- `note`
- `sequence`

Campos de materiales copiados por cada actividad:

- `sequence`
- `plan_line_material_id`
- `product_id`
- `product_uom_id`
- `estimated_quantity`
- `note`

## Workflow del aviso

El aviso representa una necesidad detectada, alerta o requerimiento inicial. La ejecución formal del trabajo se gestiona en la Orden de Trabajo estándar `maintenance.request`, no directamente en el aviso.

Estados funcionales:

```text
Nuevo
  ├─ Tomar para evaluación → En evaluación
  └─ Rechazar → Rechazado

En evaluación
  ├─ Generar OT → Con OT creada + crea Orden de Trabajo
  └─ Rechazar → Rechazado

Con OT creada
  ├─ Ver OT
  └─ Cerrar aviso → Cerrado, solo si la OT está en una etapa terminada

Rechazado
  └─ Sin acciones operativas normales

Cerrado
  └─ Sin acciones operativas normales
```

Valores técnicos de estado:

```text
pending_evaluation → approved → in_progress → closed
pending_evaluation → rejected
approved → rejected
```

Transiciones permitidas declaradas en `_allowed_state_transitions`:

```python
{
    'pending_evaluation': {'approved', 'rejected'},
    'approved': {'in_progress', 'rejected'},
    'in_progress': {'closed'},
    'in_review': {'closed'},  # compatibilidad con avisos antiguos
}
```

Acciones operativas normales:

- `action_take_for_evaluation()`
- `action_reject()`
- `action_create_maintenance_request()`
- `action_view_maintenance_request()`
- `action_close()`

`action_start()` y `action_review()` no se usan como acciones operativas del aviso; la programación, ejecución y revisión pertenecen a la OT.

Regla crítica:

No se debe escribir `state` directamente. El método `write()` bloquea cambios manuales salvo que el contexto tenga:

```python
allow_alert_state_write=True
```

## Solicitud de Mantención simple

La nueva `barca.maintenance.request` representa el requerimiento inicial de mantención creado por un usuario autorizado. No reemplaza la OT estándar. Su objetivo es capturar vehículo/equipo, solicitante, prioridad sugerida, planta y lugar detallado, estado del vehículo y descripción de la necesidad. La fecha de solicitud es la fecha actual y el equipo de mantenimiento queda bloqueado porque se deriva automáticamente del vehículo.

Un programador o administrador puede usar `action_create_alert()` para generar un aviso `barca.maintenance.alert` desde esa solicitud. El aviso queda con `source_type = request`, `source_reference` con el número de solicitud y `source_request_id` con el vínculo técnico al origen.


## Checklist

El modelo `barca.maintenance.checklist` crea un formulario inicial similar a la Solicitud de Mantención simple, pero agrega tipo de vehículo, hora de carga de combustible, odómetro, observaciones y líneas de puntos de control. Al seleccionar `checklist_type`, el sistema regenera las líneas desde `barca.maintenance.checklist.item` y evita mezclar puntos de distintos tipos.

Al guardar un checklist en estado `new`, el sistema evalúa automáticamente las líneas. Si existe al menos una línea marcada como `no`, crea un `barca.maintenance.alert` con `source_type = checklist`, `source_reference` igual al número del checklist y `checklist_id` como vínculo técnico al origen. La descripción del aviso se toma desde `observations` cuando existe; si está vacía se usa un texto automático del checklist. Los puntos de control no se copian al aviso.

Si no existe ningún punto marcado como `no`, el guardado solo conserva los datos del checklist y no genera aviso. La vista operativa mantiene un único botón explícito **Guardar**; la generación de aviso ya no requiere presionar una acción separada.

## Creación de OT

Desde un aviso en evaluación se puede crear una OT estándar `maintenance.request`, visible funcionalmente como Orden de Trabajo.

Reglas:

- El aviso debe estar en estado técnico `approved` / funcional `En evaluación`.
- No debe tener ya `maintenance_request_id`.
- Debe existir `equipment_id`.

Valores creados:

- `name`: número del aviso.
- `request_date`: fecha actual.
- `maintenance_type`: `corrective`.
- `description`: descripción del aviso + resumen de actividades.
- `equipment_id`: equipo asociado al vehículo.

Después de crear la OT:

1. Guarda `maintenance_request_id` en el aviso.
2. Guarda `barca_alert_id` en la OT.
3. Copia cada `barca.maintenance.alert.line` a una actividad ejecutable `barca.maintenance.workorder.line`.
4. Copia cada `barca.maintenance.alert.line.material` a un material ejecutable `barca.maintenance.workorder.line.material`.
5. Pasa el aviso a estado técnico `in_progress` / funcional `Con OT creada`.


## Copia de actividades y materiales a la OT

La pestaña **Actividades** de la OT estándar muestra líneas `barca.maintenance.workorder.line`. Cada línea conserva los datos técnicos copiados desde la actividad del aviso: ubicación técnica, tipo de intervención, actividad, duración estimada, descripción/instrucciones, observaciones y estado operativo (`pending`, `in_progress`, `notified`, `closed`).

Cada actividad de OT contiene una subpestaña de **Materiales / Repuestos / Kits** con líneas `barca.maintenance.workorder.line.material`. Se copian producto `product.product`, unidad de medida, cantidad estimada, secuencia, nota y referencia al material del aviso (`alert_line_material_id`). Los kits siguen tratándose como productos íntegros y no se explotan en componentes. La grilla principal de actividades de la OT muestra **N° materiales** y **Materiales** para revisar rápidamente qué productos ejecutables tiene cada actividad.

Las cantidades operativas de materiales de OT deben ser mayores o iguales a cero y la unidad de medida debe pertenecer a la categoría de la unidad base del producto. Producto, cantidad estimada y observaciones pueden editarse en la OT; también pueden agregarse o eliminarse materiales manualmente sin modificar el aviso origen.

## Relación entre aviso y OT

La OT gestiona su propio ciclo de programación, ejecución, revisión y cierre. Cambiar la etapa de la OT no mueve automáticamente el aviso a revisión. El aviso permanece en `Con OT creada` hasta que el usuario lo cierre explícitamente con `action_close()`.

## Cierre del aviso PM

Al cerrar (`action_close()`):

1. Pasa a estado `closed`.
2. Registra `closed_by_id` y `close_date`.
3. Si el aviso viene de PM (`source_type == 'pm'`), actualiza medidores del vehículo:
   - `x_odometer_last_service`
   - `x_last_exit_date`
   - `x_hours_last_service`

Regla importante: nunca retrocede valores; solo actualiza si el valor del aviso es mayor que el valor actual del vehículo.

## Fase 4: operación y notificación de actividades de OT

Cada actividad ejecutable de una OT (`barca.maintenance.workorder.line`) sigue el ciclo operativo básico:

```text
Pendiente → En ejecución → Notificada → Cerrada
```

Acciones disponibles:

- **Iniciar**: cambia una actividad `pending` a `in_progress`. Se permite que varias actividades de la misma OT estén simultáneamente en ejecución; Fase 4 no impone una restricción de actividad única en curso.
- **Notificar**: exige descripción de lo realizado, resultado y cantidades de materiales no negativas; cambia la actividad `in_progress` a `notified` y registra fecha/hora y usuario notificador.
- **Cerrar línea**: cambia una actividad `notified` a `closed`.
- **Reabrir a pendiente**: solo para administrador o programador Barca; vuelve la actividad a `pending` y limpia fecha/usuario de notificación, conservando descripción, resultado, materiales y cantidades informadas.

La pestaña **Materiales / Repuestos / Kits** de la actividad de OT muestra el detalle estructurado de materiales, repuestos o kits. Mantiene visibles las cantidades `estimated_quantity`, `reserved_quantity`, `withdrawn_quantity`, `consumed_quantity` y `returned_quantity`, además de UdM y observación, como preparación para Fase 5 y Fase 6. En Fase 4 esas cantidades son datos manuales/estructurales y no ejecutan operaciones logísticas.

La OT calcula total de actividades, actividades notificadas y actividades cerradas. El botón **Enviar a revisión** valida que exista al menos una actividad y que todas estén `notified` o `closed` (cerrada implica que ya fue notificada). Si la validación pasa, publica un mensaje en chatter cuando está disponible y muestra una notificación indicando que la OT queda lista para revisión. Esta fase no realiza cierre definitivo de la OT ni cambia etapas estándar si no hay una etapa segura identificada.

La descripción de la OT puede conservar el resumen textual concatenado de actividades para lectura rápida y compatibilidad, pero la fuente operacional principal del trabajo vive en las líneas reales `barca_activity_line_ids` y en sus materiales `barca.maintenance.workorder.line.material`; no se debe volver a una lógica basada solo en texto.

Fase 4 no implementa ni dispara:

- Reservas.
- Retiros de bodega.
- `stock.move`.
- `stock.picking`.
- Compras.
- Devoluciones.
- Consumos reales de inventario.


## Fase 5: reserva de materiales desde la OT

Desde la OT estándar `maintenance.request` se puede crear una reserva de materiales presionando el botón **Reservar materiales**, visible solo cuando no existe reserva previa.

### Qué hace la reserva

1. Recopila todos los materiales (`barca.maintenance.workorder.line.material`) de todas las actividades de la OT, considerando solo líneas con `product_id` y `estimated_quantity > 0`.
2. Agrupa las líneas por producto (`product_id`) y unidad de medida (`product_uom_id`).
3. Crea un `stock.picking` de tipo operación interna vinculado a la OT (`origin = "OT <nombre>"`).
4. Crea un `stock.move` por cada grupo producto/UdM con la cantidad total estimada.
5. Confirma el picking con `action_confirm()` y asigna stock con `action_assign()`.
6. **No valida el picking**: el stock físico no se descuenta en Fase 5.
7. Actualiza `reserved_quantity` en las líneas de material de OT con distribución secuencial.
8. Publica resumen en el chatter de la OT.

### Estados de materiales

- `no_materials`: no hay materiales válidos.
- `pending_reservation`: estado inicial (antes de reservar).
- `reserved`: reserva completa (total reservado == total solicitado).
- `partial`: reserva parcial (algo reservado, menos que lo solicitado).
- `missing`: sin stock suficiente (reservado == 0).

### Determinación de ubicaciones

- **Origen**: `warehouse.lot_stock_id` (stock principal del almacén).
- **Tipo de picking**: `warehouse.int_type_id`; si no existe, se busca cualquier tipo `internal` activo para la compañía.
- **Destino**: se busca primero una ubicación interna cuyo nombre contenga "mantenimiento"; si no existe, se usa `picking_type.default_location_dest_id`. Si destino == origen, se lanza `ValidationError`.

No se crean ubicaciones automáticamente.

### Distribución de reserved_quantity

Como los movimientos se agrupan, la cantidad reservada se distribuye secuencialmente entre las líneas originales del mismo producto/UdM, en orden por actividad/secuencia/id, hasta agotar la reserva disponible. Ninguna línea recibe más que su `estimated_quantity` ni valor negativo.

### Restricciones

- No se permite crear una segunda reserva si ya existe `barca_material_picking_id`.
- El retiro físico se implementará en Fase 6.
- La devolución y consumo real se implementarán en Fase 6.
- Los kits se reservan como productos normales sin explosión de componentes.

### Campos en maintenance.request

| Campo | Descripción |
|---|---|
| `barca_material_picking_id` | Many2one al `stock.picking` de reserva |
| `barca_material_state` | Estado de la reserva (selection) |
| `barca_pending_material` | True si estado es `partial` o `missing` |
| `barca_material_picking_count` | Integer calculado para smart button |


## Fase 6: entrega, consumo y cierre de materiales (versión simplificada Barca)

Barca opera con una bodega simple. No se implementa flujo complejo de inventario. La entrega de materiales es un registro operativo sin generación de picking adicional.

### Flujo de materiales en Fase 6

```
[Fase 5: reservado] → Entregar materiales → Registrar consumo real → Cerrar materiales
```

La Fase 6 funciona aunque no se haya ejecutado la Fase 5 (sin reserva previa).

### Botón "Entregar materiales" (`action_barca_deliver_materials`)

- Si `reserved_quantity > 0` → usa `reserved_quantity` como `withdrawn_quantity`.
- Si `reserved_quantity == 0` → usa `estimated_quantity` como `withdrawn_quantity`.
- Marca `barca_material_withdrawn = True`, registra fecha y usuario.
- Publica resumen en chatter indicando base usada (reserva o estimado).
- No se crea picking adicional.
- No se puede ejecutar dos veces.

### Registro de consumo real

El campo `consumed_quantity` en cada línea de material (`barca.maintenance.workorder.line.material`) es editable. Representa la cantidad realmente utilizada por el técnico. No bloquea la notificación de actividades.

### Botón "Cerrar materiales" (`action_barca_close_materials`)

- Requiere que `barca_material_withdrawn == True`.
- Valida que `consumed_quantity <= withdrawn_quantity` por línea.
- Calcula `returned_quantity = withdrawn_quantity - consumed_quantity`.
- Marca `barca_material_closed = True`, registra fecha y usuario.
- Publica en chatter: totales entregado, consumido, devuelto, costo estimado, costo real, diferencia.
- No crea picking de devolución.

### Costos

- `barca_estimated_material_cost` = suma de `estimated_quantity * product_id.standard_price`.
- `barca_real_material_cost` = suma de `consumed_quantity * product_id.standard_price`.
- Si el producto no tiene `standard_price`, contribuye con 0.
- Ambos son campos computados almacenados.

### Campos nuevos en `maintenance.request` (Fase 6)

| Campo | Tipo | Descripción |
|---|---|---|
| `barca_material_withdrawn` | Boolean | Materiales entregados |
| `barca_material_delivery_date` | Datetime | Fecha entrega |
| `barca_material_delivered_by_id` | Many2one res.users | Entregado por |
| `barca_material_closed` | Boolean | Ciclo cerrado |
| `barca_material_closed_date` | Datetime | Fecha cierre |
| `barca_material_closed_by_id` | Many2one res.users | Cerrado por |
| `barca_material_note` | Text | Observación libre |
| `barca_estimated_material_cost` | Float | Costo estimado calculado |
| `barca_real_material_cost` | Float | Costo real calculado |

### Fase 6 NO implementa

- Picking formal de devolución.
- Órdenes de compra.
- Aprobaciones de bodega.
- Múltiples bodegas.
- Explosión de kits.
- Recepción de compras.
- Fase 7.
