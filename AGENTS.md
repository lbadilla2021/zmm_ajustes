# AGENTS.md — Guía obligatoria para IA/Codex

Este repositorio contiene el módulo personalizado `zmm_ajustes` de Odoo 18 Community para la gestión de mantención de Barca SpA.

Antes de modificar código, leer en este orden:

1. `docs_codex/00_contexto_general.md`
2. `docs_codex/01_mapa_del_modulo.md`
3. `docs_codex/02_modelo_de_datos.md`
4. `docs_codex/03_flujos_de_negocio.md`
5. `docs_codex/04_reglas_tecnicas_odoo18.md`
6. `docs_codex/05_seguridad_menus_roles.md`
7. `docs_codex/06_importacion_datos_csv.md`
8. `docs_codex/07_riesgos_y_errores_conocidos.md`
9. `docs_codex/08_checklist_antes_de_cambiar.md`

Reglas críticas:

- No asumir modelos de Odoo antiguos. El módulo es para Odoo 18.
- No usar `fleet.vehicle.cost`; en Odoo 18 este modelo no debe ser usado.
- Validar siempre que cada campo usado en XML exista en Python.
- No cambiar estados de `barca.maintenance.alert` escribiendo directamente `state`; usar acciones del modelo.
- No romper la relación automática `fleet.vehicle` ↔ `maintenance.equipment`.
- No eliminar campos `x_` de `fleet.vehicle`; son base para triggers y cierre de avisos PM.
- No cambiar el sentido del flujo PM: Plan → Aviso → OT `maintenance.request` → Revisión → Cierre.
- Toda mejora debe mantener compatibilidad con datos ya cargados por CSV y con los XML IDs generados para ubicaciones técnicas.
- Los cambios deben ser mínimos, explícitos y compatibles con actualización del módulo (`-u zmm_ajustes`).
