# 07 — Riesgos y errores conocidos

## 1. Usar modelos obsoletos de Odoo

No usar `fleet.vehicle.cost`. En Odoo 18 este modelo no debe asumirse disponible.

Si se necesita historial de servicios/costos, revisar modelos vigentes como `fleet.vehicle.log.services` y confirmar en la base real.

## 2. Campos en XML que no existen en Python

Error típico:

```text
Unknown field ...
```

Antes de tocar vistas XML:

1. Verificar modelo de la vista.
2. Verificar campos declarados en Python.
3. Verificar campos heredados desde módulos estándar.
4. Verificar que el archivo Python esté importado en `models/__init__.py`.

## 3. XML ID de vista heredada no encontrado

Especial cuidado con:

```xml
maintenance.hr_equipment_request_view_form
fleet.fleet_vehicle_view_form
```

Si falla instalación o actualización, revisar XML IDs reales en `ir.model.data`.

## 4. Cambio directo de estado de avisos

`barca.maintenance.alert.write()` bloquea escritura directa de `state` si no viene contexto `allow_alert_state_write=True`.

No crear importaciones, wizards o botones que hagan:

```python
alert.write({'state': 'closed'})
```

Usar:

```python
alert.action_close()
```

O, si es una transición interna justificada:

```python
alert.with_context(allow_alert_state_write=True).write({'state': '...'})
```

## 5. Duplicidad de avisos PM

La lógica impide más de un aviso PM abierto por vehículo.

Esto es intencional, pero puede sorprender si existen varios planes vencidos para un mismo vehículo. El primer plan evaluado genera el aviso y bloquea los demás.

El cron ordena por menor trigger.

## 6. Cierre de OT y cierre del aviso

La OT gestiona programación, ejecución y revisión. El aviso no pasa automáticamente a `in_review` cuando cambia la OT.

El aviso permanece en `Con OT creada` y debe cerrarse explícitamente. `action_close()` valida que exista una OT asociada y que la OT esté en una etapa terminada (`stage_id.done`), equivalente funcionalmente a Reparado o Desechar.

## 7. Equipo de mantenimiento requerido para crear OT

`action_create_maintenance_request()` exige `equipment_id`.

El módulo crea equipos automáticamente al crear vehículos y también sincroniza existentes en hook. Sin embargo, si hay datos antiguos o inconsistentes, puede faltar equipo.

Diagnóstico:

```python
fleet.vehicle sin maintenance.equipment asociado
```

Solución: ejecutar lógica equivalente a `sync_existing_vehicle_equipment()`.

## 8. Riesgo con `ondelete='cascade'` en `maintenance.equipment.vehicle_id`

El campo `vehicle_id` en `maintenance.equipment` usa `ondelete='cascade'`.

Si se elimina un vehículo, puede eliminarse el equipo asociado. Revisar impacto si existen OTs históricas asociadas al equipo.

## 9. Multiempresa incompleta

Hay `company_id` en algunos modelos, pero no se observan reglas de registro por compañía.

Si se usará con varias compañías, diseñar `ir.rule` antes de producción.

## 10. CSV con códigos repetidos

El CSV puede contener padre e hijo con el mismo código y nombre, por ejemplo `MOTOR / MOTOR`.

Puede no fallar por SQL, pero complica XML IDs, imports y trazabilidad.

## 11. `level` computado tratado como dato manual

`hooks.py` entrega `level: 1` y `level: 2`, pero `level` se calcula según `parent_id`.

No basar lógica de negocio en valores manuales de `level`; confiar en el compute.

## 12. Campo `x_downtime_total` no calcula tiempo real

Actualmente `_compute_downtime()` asigna `0.0` siempre.

Si se requiere KPI de tiempo fuera de servicio, implementar cálculo real entre entrada/salida o según eventos de taller.

## 13. `x_odometer_next_service` es fijo +5000

Actualmente se calcula como:

```python
x_odometer_last_service + 5000
```

Esto no necesariamente refleja planes dinámicos. Si se quiere precisión, debería conectarse con planes activos o próximo PM aplicable.

## 14. `maintenance_type` de OT creada como `corrective`

Aunque el aviso venga de PM, la OT se crea con:

```python
maintenance_type = 'corrective'
```

Puede ser una decisión práctica, pero conceptualmente podría ser `preventive` si el estándar de Odoo y la operación lo permiten.

Antes de cambiarlo, revisar impacto en reportes estándar.
