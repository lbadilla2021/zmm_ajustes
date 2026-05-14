# 09 — Prompt base para Codex

Usa este prompt al iniciar una tarea nueva sobre el módulo.

```text
Estás trabajando sobre el módulo personalizado `zmm_ajustes` de Odoo 18 Community para Barca SpA.

Antes de proponer o aplicar cambios, lee obligatoriamente:

- AGENTS.md
- docs_codex/00_contexto_general.md
- docs_codex/01_mapa_del_modulo.md
- docs_codex/02_modelo_de_datos.md
- docs_codex/03_flujos_de_negocio.md
- docs_codex/04_reglas_tecnicas_odoo18.md
- docs_codex/05_seguridad_menus_roles.md
- docs_codex/06_importacion_datos_csv.md
- docs_codex/07_riesgos_y_errores_conocidos.md
- docs_codex/08_checklist_antes_de_cambiar.md

Contexto funcional:

El módulo gestiona mantención de flota/equipos para Barca SpA. Extiende `fleet.vehicle`, `maintenance.equipment` y `maintenance.request`, y agrega modelos propios para ubicaciones técnicas, actividades, planes preventivos, líneas de plan, kits, avisos y líneas de aviso.

Flujo principal:

Plan PM → evaluación por km/días/horas → aviso de mantención → aprobación/rechazo → creación de OT `maintenance.request` → ejecución → revisión → cierre → actualización de medidores del vehículo.

Reglas críticas:

1. El proyecto es Odoo 18 Community.
2. No usar `fleet.vehicle.cost` ni modelos obsoletos.
3. No escribir directamente `state` en `barca.maintenance.alert`; usar acciones.
4. Validar que todo campo XML exista en Python.
5. Mantener la relación 1:1 `fleet.vehicle` ↔ `maintenance.equipment`.
6. Mantener compatibilidad con CSV de ubicaciones técnicas y XML IDs por código.
7. No romper seguridad por grupos Barca.
8. No hacer refactors grandes si la tarea pide un ajuste puntual.
9. Todo cambio debe ser compatible con actualización del módulo mediante `-u zmm_ajustes`.

Tarea específica:

[DESCRIBIR AQUÍ LA TAREA]

Entrega esperada:

- Diagnóstico breve.
- Archivos a modificar.
- Cambios propuestos o patch.
- Riesgos.
- Pruebas manuales sugeridas.
- Comando de actualización del módulo.
```
