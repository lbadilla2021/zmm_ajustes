# Vinculación Vehículos Flota ↔ Equipos Mantenimiento

## Contexto

Cada vehículo en el módulo Flota debe tener un registro espejo en
Mantenimiento > Equipos, vinculado por el campo `vehicle_id`.
Este vínculo es el que permite al módulo Barca Mantenimiento generar
avisos y OT asociados a un vehículo concreto.

**Los vehículos nuevos se vinculan automáticamente** al crearse (el
módulo crea el equipo en el mismo momento). Este procedimiento es solo
para vincular la flota existente antes de instalar el módulo.

---

## Paso 1 — Exportar vehículos desde Flota

1. Ir a **Flota > Vehículos > Vehículos**.
2. Seleccionar todos los registros (checkbox encabezado).
3. Menú **Acción > Exportar**.
4. En el diálogo de exportación:
   - Activar **"Exportar con External ID"** (imprescindible).
   - Agregar los campos en este orden:
     - `id`  ← columna clave, es el External ID
     - `Identificador de vehículo` (`x_vehicle_identifier`)  ← ID numérico del registro para trazabilidad
     - `Nombre` (`name`)
     - `Matrícula` (`license_plate`)
     - `Categoría / External ID` (`category_id/id`)
     - `Categoría / Nombre` (`category_id/name`)
     - `Código interno` (`x_internal_code`)  ← opcional, ayuda a identificar
5. Exportar como **CSV**.

El archivo resultante tendrá en la columna `id` valores del tipo:
`__export__.fleet_vehicle_42`

Además, la columna `x_vehicle_identifier` mostrará el identificador numérico interno del vehículo (por ejemplo `42`).

Guardar ese archivo — se usará como referencia en el Paso 2.

---

## Paso 2 — Preparar el archivo de importación de Equipos

Crear un CSV con las siguientes columnas usando los `id` obtenidos
en el Paso 1:

```
id,name,vehicle_id/id
__export__.fleet_vehicle_42,Camión 001,__export__.fleet_vehicle_42
__export__.fleet_vehicle_43,Camioneta 002,__export__.fleet_vehicle_43
```

Reglas:
- **`id`**: puede ser cualquier identificador único. La convención más
  simple es reutilizar el mismo External ID del vehículo.
- **`name`**: nombre del equipo. Se recomienda usar el mismo nombre del
  vehículo para facilitar la búsqueda.
- **`vehicle_id/id`**: External ID del vehículo tal como aparece en
  la exportación del Paso 1. Esta columna es la que crea el vínculo.

El archivo `plantilla_importacion_equipos.csv` incluido en esta carpeta
muestra la estructura con filas de ejemplo.

---

## Paso 3 — Importar Equipos en Mantenimiento

1. Ir a **Mantenimiento > Equipos**.
2. Menú **Acción > Importar** (o botón Importar en la vista lista).
3. Subir el CSV preparado en el Paso 2.
4. Verificar que Odoo mapee correctamente las columnas.
5. Hacer clic en **Importar**.

---

## Verificación

Después de importar, para cada equipo debe aparecer el campo
**Vehículo** apuntando al registro de Flota correspondiente.

Desde la ficha del vehículo en Flota > pestaña **Mantención Barca**
también es posible verificar la vinculación.

---

## Notas

- Si ya existen equipos creados manualmente (sin `vehicle_id`), no se
  borran — simplemente quedan sin vínculo. Se pueden vincular
  manualmente editando el equipo y seleccionando el vehículo.
- El constraint `unique(vehicle_id)` en el modelo impide crear dos
  equipos para el mismo vehículo. Si al importar aparece ese error,
  significa que el equipo ya existe y solo falta agregar el `vehicle_id`
  (hacer un update, no un create).
- Para actualizar registros existentes vía importación, incluir el
  `id` del equipo existente en la columna `id` del CSV.
