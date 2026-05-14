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

El comentario indica que en Odoo 18 se usa la vista formulario vigente del módulo `maintenance`.

Antes de cambiar este XML ID, confirmar en la instalación real:

```bash
docker exec -it <odoo_container> odoo shell -d <db>
```

y consultar `ir.model.data` si es necesario.

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
