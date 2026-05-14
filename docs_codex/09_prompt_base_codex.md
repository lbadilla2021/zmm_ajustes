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

El módulo gestiona mantención de flota/equipos para Barca SpA. Extiende `fleet.vehicle`, `maintenance.equipment` y `maintenance.request`, y agrega modelos propios para ubicaciones técnicas, actividades, planes preventivos, líneas de plan, kits, solicitudes simples de mantención, avisos y líneas de aviso.

Flujo principal:

Solicitud de Mantención simple / checklist / Plan PM → aviso de mantención → aprobación/rechazo → creación de OT `maintenance.request` → ejecución → revisión → cierre → actualización de medidores del vehículo cuando aplique.

Reglas críticas:

1. El proyecto es Odoo 18 Community.
2. No usar `fleet.vehicle.cost` ni modelos obsoletos.
3. No escribir directamente `state` en `barca.maintenance.alert`; usar acciones.
4. Validar que todo campo XML exista en Python.
5. Mantener la relación 1:1 `fleet.vehicle` ↔ `maintenance.equipment`.
6. Las ubicaciones técnicas se crean/importan manualmente; no reintroducir carga runtime desde CSV. Mantener XML IDs automáticos por código.
7. No romper seguridad por grupos Barca.
8. No hacer refactors grandes si la tarea pide un ajuste puntual.
9. Todo cambio debe ser compatible con actualización del módulo mediante `-u zmm_ajustes`.
10. `maintenance.request` se usa funcionalmente como **Orden de Trabajo**; no cambiar innecesariamente su modelo técnico ni los XML IDs existentes asociados a la opción de OT.
11. `barca.maintenance.request` es la **Solicitud de Mantención** simple: requerimiento inicial de usuario, con fecha actual bloqueada, equipo bloqueado/autocargado desde vehículo, Planta y Lugar detallado, Estado del vehículo (`operativo` / `no_operativo`) y capacidad de generar un aviso con `source_type = request`.
12. `barca.maintenance.checklist` es el **Checklist** operativo: se ubica bajo **Orígenes Avisos**, carga líneas desde `barca.maintenance.checklist.item` por tipo de vehículo, guarda respuestas Sí/No y al guardar genera automáticamente aviso con `source_type = checklist` si existe al menos un No.
13. Menús principales bajo **Mantención Barca**: Orígenes Avisos, Mantenimiento, Informes, Equipos, Configuración. Bajo **Orígenes Avisos**: Planes de Mantenimiento, Solicitud de Mantención, Checklist. Bajo **Mantenimiento**: Avisos, Orden de Trabajo, Calendario Mantenimiento. Bajo **Informes**: Solicitudes de mantenimiento.

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
