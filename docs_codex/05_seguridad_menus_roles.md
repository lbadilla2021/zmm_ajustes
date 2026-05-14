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

Todos implican `base.group_user`.

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

## Menús por rol

Archivo: `views/base_views.xml` y `views/maintenance_alert_views.xml`.

### Menú raíz

`Mantención Barca` visible para todos los grupos Barca.

### Mantenimiento

Visible para todos los grupos Barca.

Submenús:

- `Planes de Mantenimiento`: Programador, Admin.
- `Avisos`: Conductor, Programador, Ejecutor, Bodega, Admin.
- `Solicitudes de Mantenimiento`: Programador, Admin.
- `Calendario Mantenimiento`: Programador, Admin.

### Equipos

Visible para Programador, Ejecutor, Admin.

### Informes

Visible para Programador, Admin.

### Configuración

Visible solo para Admin.

Submenús de configuración:

- Ubicaciones técnicas: Admin.
- Tipos de intervención: Admin.
- Actividades: Programador, Admin.
- Kits: Bodega, Programador, Admin.
- Categorías de equipos: Admin.
- Equipos de mantenimiento: Admin.

## Botones de aviso por rol

Archivo: `views/maintenance_alert_views.xml`.

- `Aprobar`: Programador, Admin.
- `Rechazar`: Programador, Admin.
- `Iniciar ejecución`: Ejecutor, Programador.
- `Crear OT`: Programador, Admin.
- `Enviar a revisión`: Ejecutor.
- `Cerrar`: Programador, Admin.

## Consideraciones para cambios

Cuando se agregue un modelo nuevo:

1. Crear ACL en `ir.model.access.csv`.
2. Evaluar si requiere reglas de registro (`ir.rule`). Actualmente no se observan reglas de registro.
3. Agregar menús con grupos explícitos.
4. Agregar botones con `groups` si ejecutan acciones sensibles.
5. Verificar que los usuarios no vean menús sin permisos reales.

## Riesgo actual

No se observan reglas de registro multiempresa. Aunque algunos modelos tienen `company_id`, el aislamiento por compañía no está reforzado con `ir.rule` en este módulo.

Si el sistema se usará multiempresa real, se debería diseñar seguridad por compañía antes de producción amplia.
