# 06 — Importación manual de ubicaciones técnicas

## Decisión vigente

El módulo **ya no carga ubicaciones técnicas desde un CSV incluido en el código**.

Las ubicaciones técnicas (`barca.technical.location`) se deben crear o importar manualmente después de instalar el módulo, usando la interfaz de Odoo o el importador estándar sobre el menú:

```text
Configuración → Ubicaciones técnicas
```

El archivo histórico `data/technical_locations.csv` fue eliminado y no debe volver a ser una dependencia de instalación/actualización del módulo.

## Hook inicial vigente

Archivo:

```text
hooks.py
```

Función declarada en `__manifest__.py`:

```python
'post_init_hook': 'sync_existing_vehicle_equipment'
```

Este hook **solo** sincroniza vehículos existentes con `maintenance.equipment`. No crea ubicaciones técnicas.

## Campos sugeridos para importación manual

Para importar ubicaciones técnicas manualmente, preparar un archivo para el importador estándar de Odoo con campos equivalentes a:

```text
name
code
category_id
parent_code
kit_id
estimated_useful_life
reference_supplier_id
note
```

Notas:

- `name` y `code` son obligatorios.
- `category_id` es obligatorio y debe apuntar a una categoría existente de `fleet.vehicle.model.category`.
- `parent_code` puede usarse para enlazar una sububicación con una ubicación padre ya creada/importada.
- Si se usa `parent_code`, importar primero los padres y luego los hijos.

## XML IDs automáticos

El modelo `barca.technical.location` implementa `_ensure_external_ids()`.

Al crear o actualizar una ubicación técnica, el modelo crea/actualiza registros en `ir.model.data` con:

- `module`: `zmm_ajustes`
- `name`: código de ubicación técnica
- `model`: `barca.technical.location`
- `res_id`: ID de la ubicación
- `noupdate`: True

Esto permite que las ubicaciones importadas manualmente mantengan referencias estables por código.

## Cuidado con códigos duplicados

`_ensure_external_ids()` usa `code` como nombre de XML ID.

Recomendación: mantener `code` único globalmente. Si se repite el mismo código en ubicaciones distintas, la segunda ubicación no tendrá un XML ID independiente con ese mismo código.

## Sincronización vehículo-equipo

`sync_existing_vehicle_equipment()` recorre todos los `fleet.vehicle` existentes y crea un `maintenance.equipment` si no hay uno asociado.

Esto es importante porque los flujos de Aviso → OT necesitan `equipment_id`.

## Consideración sobre `post_init_hook`

El hook se ejecuta al instalar el módulo. Si solo se actualiza el módulo (`-u zmm_ajustes`), no se debe asumir que volverá a ejecutarse.

Si se requiere sincronizar vehículos existentes en un ambiente ya instalado, ejecutar una acción manual, script de migración o server action que llame una lógica equivalente a `sync_existing_vehicle_equipment()`.
