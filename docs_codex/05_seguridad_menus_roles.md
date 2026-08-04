# 05 — Seguridad, menús y roles

## Grupos definidos

Archivo: `security/res_groups.xml`.

Categoría del módulo:

- `Mantención Barca`

Grupos:

| XML ID | Nombre |
|---|---|
| `group_barca_conductor` | Barca / Conductor |
| `group_barca_programador` | Barca / Programador |
| `group_barca_ejecutor` | Barca / Ejecutor |
| `group_barca_bodega` | Barca / Bodega |
| `group_barca_admin` | Barca / Administrador |

Todos implican `base.group_user`. AdemÃ¡s, `group_barca_programador`
implica `fleet.fleet_group_user` para que los selectores basados en
`fleet.vehicle`, como el campo **VehÃ­culo** en **Solicitud de MantenciÃ³n**,
puedan listar vehÃ­culos usando la seguridad estÃ¡ndar de Flotilla.

## Filosofía de permisos

El módulo usa permisos por rol operativo:

- Conductor: lectura muy limitada, principalmente avisos/ubicaciones.
- Programador: gestión operativa de planes y avisos.
- Ejecutor: ejecución/revisión de avisos y lectura de catálogos.
- Bodega: lectura de planes/avisos y edición parcial de kits.
- Administrador: control total.

## ACL principales

Archivo: `security/ir.model.access.csv`.

### Ubicaciones técnicas

- Conductor, Programador, Ejecutor, Bodega: lectura.
- Admin: lectura, escritura, creación, eliminación.

### Tipos de intervención

- Programador y Ejecutor: lectura.
- Admin: total.

### Actividades

- Programador y Ejecutor: lectura.
- Admin: total.

### Planes

- Programador: leer, escribir, crear; no eliminar.
- Ejecutor y Bodega: lectura.
- Admin: total.

### Líneas de plan

- Programador: total.
- Ejecutor y Bodega: lectura.
- Admin: total.

### Kits

- Programador y Ejecutor: lectura.
- Bodega: leer y escribir; no crear ni eliminar.
- Admin: total.

### Avisos

- Conductor: lectura.
- Programador: total.
- Ejecutor: leer y escribir; no crear ni eliminar.
- Bodega: lectura.
- Admin: total.

### Líneas de aviso

- Conductor: lectura.
- Programador: total.
- Ejecutor: leer y escribir; no crear ni eliminar.
- Bodega: lectura.
- Admin: total.

### Solicitudes y Checklist del Conductor

El Conductor puede crear, visualizar y editar solicitudes de mantención y checklists,
pero las reglas de registro limitan ambas operaciones a registros donde
`requested_by_id = user.id`. La misma restricción se propaga a las líneas del
Checklist mediante `checklist_id.requested_by_id`.

No existe una restricción por vehículo: el Conductor mantiene acceso de lectura al
catálogo completo de vehículos/equipos disponibles y puede seleccionar cualquiera al
crear un registro. El solicitante se fuerza al usuario actual al crear y no puede ser
reasignado por el Conductor desde la vista ni mediante RPC.

## Menús por rol

Archivo: `views/base_views.xml` y `views/maintenance_alert_views.xml`.

### Menú raíz

`Mantención Barca` visible para todos los grupos Barca.

### Orígenes Avisos

Visible para todos los grupos Barca.

Submenús:

- `Planes de Mantenimiento`: Programador, Admin.
- `Solicitud de Mantención`: Conductor, Programador, Ejecutor, Bodega, Admin.
- `Checklist`: Conductor, Programador, Ejecutor, Bodega, Admin.

### Mantenimiento

Visible para todos los grupos Barca.

Submenús:

- `Odómetros`: Conductor, Programador, Ejecutor, Bodega, Admin. Usa `fleet.vehicle.odometer`; los grupos Barca tienen lectura de vehículos y lectura/creación/edición de odómetros sin eliminación para operar el menú sin habilitar todo Flotilla.
- `Avisos`: Conductor, Programador, Ejecutor, Bodega, Admin.
- `Orden de Trabajo`: Programador, Admin.
- `Calendario Mantenimiento`: Programador, Admin.

### Equipos

Visible para Programador, Ejecutor, Admin. La pestaña **Documentación** muestra datos relacionados desde `fleet.vehicle` en solo lectura; la mantención de esos campos se realiza en Flotilla.

### Informes

Visible para Programador, Admin.

Submenús de informes:

- Solicitudes de mantenimiento: Programador, Admin.

### Configuración

Visible solo para Admin.

Submenús de configuración:

- Ubicaciones técnicas: Admin.
- Tipos de intervención: Admin.
- Actividades: Programador, Admin.
- Kits: Bodega, Programador, Admin.
- Categorías de equipos: Admin.
- Equipos de mantenimiento: Admin.
- Alertas: Admin en Mantención Barca; Fleet Manager/Admin en la configuración de Flotilla. Este menú administra `barca.fleet.alert.rule`, incluyendo las reglas `Modificaciones` y `Vencimientos`.
- Checklist: Admin.

### Alertas de flotilla

ACL de `barca.fleet.alert.rule`:

- `group_barca_admin`: lectura, escritura, creación y eliminación.
- `fleet.fleet_group_manager`: lectura, escritura, creación y eliminación desde la configuración estándar de Flotilla.

## Botones de aviso por rol

Archivo: `views/maintenance_alert_views.xml`.

- `Tomar para evaluación`: Programador, Admin.
- `Rechazar`: Programador, Admin.
- `Generar OT`: Programador, Admin.
- `Ver OT`: Ejecutor, Programador, Admin.
- `Cerrar aviso`: Programador, Admin. Se conserva como acción explícita compatible, aunque la OT también cierra automáticamente el aviso al llegar a **Cierre Total**, **Cierre Parcial** o **Desechar**.

Los botones **Enviar a revisión**, **Devolver a progreso**, **Cierre Total**, **Cierre Parcial** y **Desechar** pertenecen al formulario de la OT (`maintenance.request`), no al aviso.

## Consideraciones para cambios

Cuando se agregue un modelo nuevo:

1. Crear ACL en `ir.model.access.csv`.
2. Evaluar si requiere reglas de registro (`ir.rule`). Actualmente existen reglas de
   propiedad para Solicitudes y Checklist del Conductor; no existen reglas generales
   de aislamiento multiempresa.
3. Agregar menús con grupos explícitos.
4. Agregar botones con `groups` si ejecutan acciones sensibles.
5. Verificar que los usuarios no vean menús sin permisos reales.

## Riesgo actual

No se observan reglas de registro multiempresa. Aunque algunos modelos tienen `company_id`, el aislamiento por compañía no está reforzado con `ir.rule` en este módulo.

Si el sistema se usará multiempresa real, se debería diseñar seguridad por compañía antes de producción amplia.

## Aislamiento de portales web y offline

Las rutas públicas de Checklist y Solicitud de Mantención requieren una sesión Odoo válida o un token externo válido para el formulario correspondiente. Aunque los controladores usan un entorno con privilegios elevados, todas las búsquedas de registros operativos se limitan al propietario autenticado:

- Usuario Odoo: `requested_by_id` debe corresponder al usuario de la sesión.
- Token externo: `external_token_user_id` debe corresponder al usuario del token.

Este dominio se aplica al listado, detalle, edición y búsqueda idempotente por UUID offline. Un registro ajeno se responde como no encontrado y no se expone si el ID o UUID es conocido por otro usuario. Los catálogos comunes de vehículos/equipos e ítems de control permanecen disponibles para construir los formularios y no implican acceso a registros operativos ajenos.

## Bloqueo de OT para Ejecutor por estado

El rol `group_barca_ejecutor` tiene una restricción en Python, no solo en menús o vistas:

- Puede editar la OT, sus actividades y sus materiales solo cuando `maintenance.request.stage_id` corresponde a **En progreso**.
- En **Aprobada**, la OT continúa bloqueada para edición general, pero el Jefe de Taller puede ejecutar **Iniciar** sobre una actividad pendiente. Esa acción controlada es la única que cambia **Aprobada** a **En progreso** y registra el inicio.
- Si la OT está en **En revisión**, **Desechar**, **Cierre Total** o **Cierre Parcial**, el ejecutor queda bloqueado aunque conozca la URL o intente escribir por RPC.
- El botón **Enviar a revisión** es la única transición permitida para que el ejecutor cambie la OT desde **En progreso** a **En revisión**.
- El inicio de actividades se valida en Python y queda limitado a Jefe de Taller (`group_barca_ejecutor`) o Administrador Barca; Programador, Bodega y Conductor no pueden forzarlo por RPC.
- Aunque la OT esté en `in_progress`, el ejecutor no puede modificar `name`, `request_date` ni `schedule_date`.
- Programador y Administrador no quedan afectados por este bloqueo.

## Fechas de taller de la OT

Los permisos se controlan también en Python para impedir cambios por RPC o importación:

- **Fecha ingreso a taller**: editable por Jefe de Taller (`group_barca_ejecutor`) y Administrador Barca. Para el ejecutor restringido, la OT debe estar en **En progreso**.
- **Fecha salida de taller**: editable por Programador y Administrador Barca.
- **Tiempo fuera de servicio**: siempre calculado y de solo lectura.

El cierre parcial o total solo propone automáticamente la salida cuando todavía no existe; la edición posterior sigue reservada al Programador o Administrador.
