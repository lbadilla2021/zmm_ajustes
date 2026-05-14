# 06 — Importación de datos CSV y hook inicial

## Archivo CSV

Archivo:

```text
data/technical_locations.csv
```

Separador:

```text
;
```

Columnas esperadas:

```text
CATEGORIA;UBICACION TECNICA;CODIGO UBICACION;SUB UBICACION;CODIGO SUBUBICACION
```

Ejemplo:

```text
CAMIONETA;MOTOR;CAM-MOT;SISTEMA DE INYECCIÓN;CAM-MOT-INY
```

## Hook de carga

Archivo:

```text
hooks.py
```

Función:

```python
load_technical_locations(cr, registry)
```

Declarada en `__manifest__.py` como:

```python
'post_init_hook': 'load_technical_locations'
```

## Qué hace el hook

1. Abre `data/technical_locations.csv`.
2. Lee cada fila con `csv.DictReader(delimiter=';')`.
3. Busca la categoría en `fleet.vehicle.model.category` por nombre exacto.
4. Si no encuentra categoría, omite la fila y registra warning.
5. Busca o crea ubicación técnica padre.
6. Si existe sububicación, busca o crea ubicación técnica hija.
7. Al final llama `_ensure_external_ids()` sobre todas las ubicaciones.
8. Ejecuta `sync_existing_vehicle_equipment()`.

## Dependencia crítica

Las categorías de vehículos deben existir previamente en `fleet.vehicle.model.category` con nombre exacto al valor de la columna `CATEGORIA`.

Ejemplo: si el CSV dice `CAMIONETA`, debe existir una categoría con nombre exacto `CAMIONETA`.

## Reglas de creación

### Nodo padre

Se busca por:

```python
name = UBICACION TECNICA
category_id = categoría encontrada
parent_id = False
```

Si no existe, se crea con:

```python
name = UBICACION TECNICA
code = CODIGO UBICACION
category_id = category.id
```

### Nodo hijo

Si `SUB UBICACION` viene informado, se busca por:

```python
name = SUB UBICACION
category_id = category.id
parent_id = parent.id
```

Si no existe, se crea con:

```python
name = SUB UBICACION
code = CODIGO SUBUBICACION
category_id = category.id
parent_id = parent.id
```

## XML IDs automáticos

El modelo `barca.technical.location` implementa `_ensure_external_ids()`.

Crea registros en `ir.model.data` con:

- `module`: `zmm_ajustes`
- `name`: código de ubicación técnica
- `model`: `barca.technical.location`
- `res_id`: ID de la ubicación
- `noupdate`: True

Esto facilita imports posteriores usando códigos estables.

## Cuidado con códigos duplicados

Actualmente `_ensure_external_ids()` usa `code` como nombre XML ID.

Si dos ubicaciones distintas tienen el mismo `code`, puede haber conflictos lógicos. El método busca por `module + name + model`, por lo que no crea duplicado exacto, pero si el mismo código se usa en otra ubicación, no creará un XML ID nuevo para la segunda.

Recomendación: mantener `code` único globalmente o ajustar la lógica para incluir categoría en el XML ID.

## Posible problema en CSV recibido

El CSV tiene filas como:

```text
CAMIONETA;MOTOR;CAM-MOT;MOTOR;CAM-MOT
```

Esto genera un padre `MOTOR` con código `CAM-MOT` y además intenta crear hijo `MOTOR` bajo `MOTOR` con el mismo código `CAM-MOT`.

No necesariamente falla por la restricción actual, porque el padre y el hijo tienen distinto `parent_id`, pero puede ser conceptualmente confuso y generar códigos repetidos.

Antes de automatizar nuevas cargas, validar si estas filas representan:

- Una ubicación padre que además debe ser seleccionable como actividad.
- O un duplicado accidental.

## Sincronización vehículo-equipo

`sync_existing_vehicle_equipment()` recorre todos los `fleet.vehicle` existentes y crea un `maintenance.equipment` si no hay uno asociado.

Esto es importante porque el flujo de avisos necesita `equipment_id` para crear OT.

## Consideración sobre `post_init_hook`

El hook se ejecuta al instalar el módulo. Si solo se actualiza el módulo (`-u zmm_ajustes`), no necesariamente se recarga el CSV.

Si se necesita recargar CSV en ambientes existentes, considerar una acción manual, wizard, script de migración o server action.
