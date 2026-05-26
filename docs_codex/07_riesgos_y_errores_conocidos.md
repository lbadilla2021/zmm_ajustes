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

El aviso permanece en `Con OT creada` y debe cerrarse explícitamente. `action_close()` valida que exista una OT asociada y que la OT esté en una etapa final distinta de **Reparado**: **Desechar**, **Cierre Total** o **Cierre Parcial**. **Reparado** se usa como revisión del programador, no como cierre final.

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

## 10. Importación manual de ubicaciones técnicas

Las ubicaciones técnicas ya no se cargan desde un CSV del módulo. Si se importan manualmente, mantener códigos únicos para no generar conflictos lógicos en los XML IDs automáticos creados por `_ensure_external_ids()`.

## 11. Campo `x_downtime_total` no calcula tiempo real

Actualmente `_compute_downtime()` asigna `0.0` siempre.

Si se requiere KPI de tiempo fuera de servicio, implementar cálculo real entre entrada/salida o según eventos de taller.

## 12. `x_odometer_next_service` es fijo +5000

Actualmente se calcula como:

```python
x_odometer_last_service + 5000
```

Esto no necesariamente refleja planes dinámicos. Si se quiere precisión, debería conectarse con planes activos o próximo PM aplicable.

## 13. `maintenance_type` de OT creada como `corrective`

Aunque el aviso venga de PM, la OT se crea con:

```python
maintenance_type = 'corrective'
```

Puede ser una decisión práctica, pero conceptualmente podría ser `preventive` si el estándar de Odoo y la operación lo permiten.

Antes de cambiarlo, revisar impacto en reportes estándar.

## 14. Botón `Enviar Avisos` revisa toda la flotilla

El botón del formulario de vehículo ejecuta `_send_expiration_alerts()`, que busca todos los `fleet.vehicle`. No usarlo como si enviara alertas solo del vehículo abierto.

## 15. Correos de flotilla dependen de destinatarios configurados

Las alertas de `Modificaciones` y `Vencimientos` no fallan si la regla existe sin destinatarios; simplemente no envían correo. Antes de reportar un problema de envío, revisar `barca.fleet.alert.rule.email_names`.

## 16. `user_has_groups()` no funciona en expresiones de vista XML

En Odoo 18, `user_has_groups()` es un método Python del ORM y no existe como campo en ningún modelo. Usarlo en atributos `readonly=`, `invisible=` genera error de validación de vista:

```text
el campo "user_has_groups" no existe en el modelo "..."
```

**Solución correcta:** usar el atributo `groups=` del campo declarando dos versiones del mismo campo — una editable para los grupos autorizados y otra `readonly="1"` para el resto. Ver sección correspondiente en `04_reglas_tecnicas_odoo18.md`.

## 17. `state` en listas inline no referencia el padre

Dentro de un `<list>` de `One2many`, `state` se evalúa en el modelo hijo. Si el campo `state` existe en el padre pero no en el hijo, Odoo lanzará error de validación de vista. Usar `parent.state` para acceder al padre. Solo hay un nivel disponible; para bisnietos usar `readonly="1"` fijo.

## 18. Estado de OT y Kanban deben usar el mismo flujo

La OT debe mostrar una sola barra de estado basada en `stage_id`, porque ese campo controla también las columnas del Kanban. No reintroducir una segunda barra `barca_state`.

El botón **Enviar a revisión** mueve la OT desde **En progreso** a **Reparado**. Mientras está en **Reparado**, el ejecutor queda bloqueado y el programador puede devolverla a **En progreso** o cerrarla como **Cierre Total** / **Cierre Parcial**.

## 19. Fecha programada obligatoria para generar OT desde aviso

Desde el módulo 1 del flujo de revisión, `action_create_maintenance_request()` exige que el aviso tenga `barca_scheduled_date` antes de crear la OT. Sin esta fecha, la acción lanza `ValidationError`. El campo es editable solo cuando el aviso está en estado `approved` (En evaluación).

## 20. Revisor de OT se resuelve automáticamente

`action_barca_send_to_review()` resuelve el revisor sin intervención del usuario:

1. `barca_alert_id.approved_by_id` — el programador que tomó el aviso (caso normal).
2. `create_uid` de la OT — fallback si no hay aviso asociado.

No hay campo editable para seleccionar el revisor manualmente.
