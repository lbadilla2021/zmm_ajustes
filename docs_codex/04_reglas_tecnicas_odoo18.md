# 04 — Reglas técnicas Odoo 18

## Compatibilidad Odoo 18

Este módulo está orientado a Odoo 18 Community.

Reglas obligatorias:

- No usar modelos obsoletos de Odoo anteriores.
- No usar `fleet.vehicle.cost`.
- Verificar XML IDs de vistas heredadas antes de modificar XML.
- Verificar que cada campo utilizado en XML exista en el modelo Python correspondiente.
- En vistas tipo lista, Odoo 18 usa `<list>`, no asumir `<tree>` como única forma válida.

## Modelo `fleet.vehicle.log.services`

El archivo `models/fleet_vehicle_log_services.py` agrega:

```python
name = fields.Char(string='Nombre')
```

Esto existe como compatibilidad para vistas o búsquedas que esperan campo `name` en `fleet.vehicle.log.services`.

No eliminar sin revisar vistas, acciones o búsquedas heredadas.

## Vista `maintenance.request`

`views/maintenance_request_views.xml` hereda:

```xml
<field name="inherit_id" ref="maintenance.hr_equipment_request_view_form"/>
```

Este XML ID corresponde al formulario estándar vigente de `maintenance.request` en Odoo 18 Community. Esa vista base ya contiene `<form><header>`, por lo que los botones propios de Barca deben insertarse con un xpath seguro sobre el header existente, por ejemplo:

```xml
<xpath expr="//form/header" position="inside">
```

No insertar un nuevo `<header>` con `//sheet position="before"` salvo que se confirme en una versión futura que la vista base ya no trae header, porque eso puede generar doble header en el formulario de OT.

## Barra única de estado en la OT

La OT (`maintenance.request`) usa una sola barra de estado: **`stage_id`**, el flujo nativo de Odoo que también controla las columnas del Kanban.

Flujo funcional vigente:

```text
Nueva solicitud → En progreso → En revisión → Cierre Total / Cierre Parcial / Desechar
```

Equivalencias Barca:

- **En progreso** reemplaza al antiguo estado Barca `En ejecución`.
- Al presionar **Enviar a revisión**, la OT pasa automáticamente a **En revisión**. Esa etapa representa la revisión del programador y mantiene el bloqueo de edición para el ejecutor.
- Si el programador devuelve la OT, vuelve desde **En revisión** a **En progreso**.
- La antigua aprobación se reemplaza por **Cierre Total** o **Cierre Parcial**.

No reintroducir una segunda barra `barca_state` en el formulario; cualquier nueva decisión de flujo debe integrarse con `stage_id`.

Para OTs Barca, `maintenance.request.write()` bloquea cualquier cambio de `stage_id` hacia etapas ajenas al flujo Barca. Además, `data/maintenance_stage_data.xml` ejecuta `_barca_sync_maintenance_stages()` para renombrar/mergear la etapa estándar **Reparado** como **En revisión** y evitar duplicados de **Desechar** en la barra de estado.

En formulario, el `statusbar` de `stage_id` queda `readonly="1"`: muestra el avance pero no permite cambiar etapa desde las flechas. En Kanban, el arrastre de tarjetas sigue permitido visualmente por Odoo, pero cada movimiento escribe `stage_id` y pasa por las mismas validaciones de `maintenance.request.write()` que los botones de acción.

## Readonly por rol en vistas de Odoo 18

En Odoo 18, `user_has_groups()` **no se puede usar** como expresión en atributos `readonly=`, `invisible=` de vistas XML. El ORM no lo expone como campo del modelo en el contexto de evaluación de vistas.

La forma correcta para controlar readonly por grupo es declarar el campo **dos veces** con el atributo `groups=`:

```xml
<!-- Editable para programador y admin -->
<field name="schedule_date" groups="zmm_ajustes.group_barca_programador,zmm_ajustes.group_barca_admin"/>
<!-- Readonly para el resto -->
<field name="schedule_date" readonly="1"
       groups="zmm_ajustes.group_barca_ejecutor,zmm_ajustes.group_barca_bodega,zmm_ajustes.group_barca_conductor"/>
```

Si el campo nativo debe ocultarse primero, usar un xpath previo con `invisible=1`.

## `parent.state` en listas inline

Cuando un campo está dentro de un `<list>` de un `One2many`, las expresiones `readonly=`, `invisible=`, `create=`, `delete=` se evalúan en el contexto del **modelo hijo**, no del padre. Para referir el estado del padre usar `parent.state`.

Solo hay **un nivel** de `parent.` disponible en Odoo 18. Para listas anidadas en dos niveles (ej: materiales dentro de actividades del aviso), usar `readonly="1"` fijo si no se puede acceder al estado del abuelo.

Ejemplo correcto:
```xml
<!-- En lista de alert_line_ids (modelo hijo = alert.line) -->
<field name="note" readonly="parent.state in ['in_progress', 'rejected', 'closed']"/>

<!-- En lista de material_line_ids dentro de alert_line (modelo hijo = alert.line.material) -->
<!-- parent = alert.line (no tiene state) → usar readonly fijo -->
<field name="product_id" readonly="1"/>
```

## Domains dinámicos

Hay dominios importantes que dependen de categoría y ubicación técnica.

Ejemplo en líneas de plan:

```python
technical_location_id domain:
[('category_id', '=?', category_id)]

activity_id domain:
[('category_id', '=?', category_id), ('technical_location_id', '=?', technical_location_id)]
```

En XML de `maintenance_plan_views.xml`, dentro del one2many se usa `parent.category_id`.

No cambiar estos dominios sin revisar:

- `models/maintenance_plan_line.py`
- `models/maintenance_activity.py`
- `views/maintenance_plan_views.xml`

## Estados de avisos

`barca.maintenance.alert.state` no debe cambiarse directamente desde XML editable, importaciones masivas o código externo.

El `write()` del modelo bloquea la escritura directa salvo contexto:

```python
allow_alert_state_write=True
```

Los botones deben llamar métodos de acción.

## Secuencia de avisos

La secuencia está en `data/maintenance_alert_sequence.xml`:

- Código: `barca.maintenance.alert`
- Prefijo: `AVS-`
- Padding: `5`

El método `create()` de `barca.maintenance.alert` asigna secuencia si `name == 'Nuevo'`.

No cambiar el código de secuencia sin ajustar `maintenance_alert.py`.

## Cron PM

El cron está en `data/cron_pm_alerts.xml`:

```xml
<field name="code">model.run_pm_scheduler()</field>
```

Esto llama el método `run_pm_scheduler()` de `barca.maintenance.plan`.

Si se cambia el nombre del método o del modelo, actualizar el XML.

## Post init hook

`__manifest__.py` declara:

```python
'post_init_hook': 'sync_existing_vehicle_equipment'
```

El hook solo crea equipos de mantenimiento para vehículos existentes que aún no tengan un `maintenance.equipment` asociado.

Las ubicaciones técnicas ya no se cargan desde CSV en el `post_init_hook`; deben crearse o importarse manualmente después de instalar el módulo.

Atención: `post_init_hook` se ejecuta al instalar, no necesariamente en cada actualización normal del módulo.

## `__pycache__`

El ZIP recibido incluye archivos `__pycache__`. No son necesarios en un módulo Odoo versionado.

Recomendación para commits:

- Excluir `models/__pycache__/`.
- Mantener `.gitignore` para evitar bytecode Python.

## Checklist de actualización

Después de cambios:

```bash
# Actualizar módulo
odoo -d <db> -u zmm_ajustes --stop-after-init

# O desde Docker, adaptando nombres:
docker exec -it <odoo_container> odoo -d <db> -u zmm_ajustes --stop-after-init
```

Revisar logs por:

- Campos inexistentes en XML.
- XML IDs no encontrados.
- Restricciones SQL.
- Errores de dominio en vistas.
- Errores de permisos ACL.

## Fase 5: stock.picking y stock.move

### Cantidad reservada en stock.move (Odoo 18)

El campo estándar para leer la cantidad ya reservada de un movimiento es `reserved_availability` (float computed). Se lee directamente sin `hasattr()` — en el ORM de Odoo, `hasattr` siempre retorna `True` aunque el campo no exista en ese modelo concreto, haciendo el fallback inalcanzable. La forma correcta es:

```python
try:
    return move.reserved_availability
except AttributeError:
    # Fallback real para versiones anteriores
    return sum(ml.reserved_uom_qty for ml in move.move_line_ids)
```

### stock.picking de tipo internal

En Odoo 18 el tipo de operación interno del warehouse es `warehouse.int_type_id`. Si no está configurado, se busca cualquier `stock.picking.type` con `code == 'internal'` activo para la compañía.

### No invocar button_validate

En Fase 5 solo se llaman `action_confirm()` y `action_assign()`. Nunca `button_validate()` ni `_action_done()`. El stock físico no se descuenta hasta Fase 6.

### Agrupación de movimientos

Los materiales de varias actividades de la OT con el mismo producto y UdM se agrupan en un solo `stock.move`. Esto respeta la práctica estándar de Odoo de no crear movimientos duplicados por producto.


## Fase 6: campos de entrega y cierre

### Campos readonly en maintenance.request

Los campos `barca_material_withdrawn`, `barca_material_closed` y fechas asociadas son `readonly=True` en el modelo Python. No se editan manualmente; solo se modifican mediante los métodos `action_barca_deliver_materials` y `action_barca_close_materials` usando `write()` interno.

### Costos computados almacenados (`store=True`)

`barca_estimated_material_cost` y `barca_real_material_cost` son `Monetary` (no Float) con `currency_field="barca_currency_id"` y `store=True`. Los depends incluyen `product_id.standard_price` para que se recalculen si cambia el precio del producto.

### No usar `button_validate` en Fase 6

La Fase 6 no valida ningún picking. El picking de reserva de Fase 5 queda en estado asignado/confirmado hasta que una futura fase lo gestione si corresponde.
