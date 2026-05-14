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
OT / Solicitud maintenance.request
```

## Creación de planes

Un plan (`barca.maintenance.plan`) puede aplicar por:

1. Categoría de vehículo (`category_id`).
2. Vehículos específicos (`vehicle_ids`).
3. Ambos a la vez.

La función `_get_plan_vehicles()` une los vehículos específicos con los vehículos de la categoría.

El plan debe tener líneas (`plan_line_ids`). Si no tiene líneas, el cron o la acción manual lo omiten.

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

Campos copiados:

- `activity_id`
- `technical_location_id`
- `intervention_type_id`
- `estimated_duration`
- `note`
- `sequence`

## Workflow del aviso

Estados:

```text
pending_evaluation → approved → in_progress → in_review → closed
pending_evaluation → rejected
approved → rejected
```

Transiciones permitidas declaradas en `_allowed_state_transitions`:

```python
{
    'pending_evaluation': {'approved', 'rejected'},
    'approved': {'in_progress', 'rejected'},
    'in_progress': {'in_review'},
    'in_review': {'closed'},
}
```

Acciones:

- `action_approve()`
- `action_reject()`
- `action_start()`
- `action_review()`
- `action_close()`
- `action_create_maintenance_request()`

Regla crítica:

No se debe escribir `state` directamente. El método `write()` bloquea cambios manuales salvo que el contexto tenga:

```python
allow_alert_state_write=True
```

## Creación de OT

Desde un aviso aprobado se puede crear una OT estándar `maintenance.request`.

Reglas:

- El aviso debe estar en estado `approved`.
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
2. Llama `action_start()` y pasa el aviso a `in_progress`.

## Paso automático a revisión desde OT

En `maintenance_request.py`, si una OT asociada cambia a una etapa plegada (`stage_id.fold`), el aviso asociado en `in_progress` pasa a `in_review`.

Esto conecta el cierre operativo de la OT con el control del aviso Barca.

## Cierre del aviso PM

Al cerrar (`action_close()`):

1. Pasa a estado `closed`.
2. Registra `closed_by_id` y `close_date`.
3. Si el aviso viene de PM (`source_type == 'pm'`), actualiza medidores del vehículo:
   - `x_odometer_last_service`
   - `x_last_exit_date`
   - `x_hours_last_service`

Regla importante: nunca retrocede valores; solo actualiza si el valor del aviso es mayor que el valor actual del vehículo.
