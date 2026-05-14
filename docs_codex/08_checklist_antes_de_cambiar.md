# 08 — Checklist antes de cambiar el módulo

## Antes de modificar

- [ ] Leer `AGENTS.md`.
- [ ] Identificar si el cambio afecta modelos propios `barca.*` o modelos estándar heredados.
- [ ] Buscar el modelo exacto en `models/`.
- [ ] Buscar vistas relacionadas en `views/`.
- [ ] Buscar permisos en `security/ir.model.access.csv`.
- [ ] Revisar si hay menús o botones con grupos.
- [ ] Revisar si el cambio afecta cron o hook.
- [ ] Confirmar compatibilidad con Odoo 18.

## Si se agrega un campo

- [ ] Agregarlo en Python.
- [ ] Importar el archivo si es nuevo en `models/__init__.py`.
- [ ] Agregarlo a vistas si corresponde.
- [ ] Si aparece en XML, confirmar que el modelo de la vista es correcto.
- [ ] Si es requerido, analizar datos existentes para evitar errores al actualizar.
- [ ] Si es computado, definir correctamente `@api.depends`.
- [ ] Si es store=True, considerar recomputación.

## Si se agrega un modelo

- [ ] Crear archivo Python en `models/`.
- [ ] Importarlo en `models/__init__.py`.
- [ ] Crear vistas XML.
- [ ] Agregar archivo XML al `data` del `__manifest__.py`.
- [ ] Crear ACL en `security/ir.model.access.csv`.
- [ ] Agregar menú/acción si corresponde.
- [ ] Considerar secuencia si necesita numeración.
- [ ] Considerar chatter si requiere trazabilidad.

## Si se cambia una vista

- [ ] Validar XML ID heredado.
- [ ] Validar modelo de la vista.
- [ ] Validar que cada campo exista.
- [ ] Validar grupos en botones y menús.
- [ ] Validar dominios dinámicos en one2many.
- [ ] En Odoo 18, preferir sintaxis compatible actual.

## Si se cambia flujo de avisos

- [ ] Revisar `_allowed_state_transitions`.
- [ ] Revisar botones en `maintenance_alert_views.xml`.
- [ ] No permitir escritura directa de `state`.
- [ ] Revisar `maintenance_request.py`, porque la OT puede mover aviso a revisión.
- [ ] Revisar `action_close()`, porque actualiza medidores del vehículo.

## Si se cambia generación PM

- [ ] Revisar `_should_generate_alert()`.
- [ ] Revisar `_create_alert_for_vehicle()`.
- [ ] Revisar prevención de duplicados.
- [ ] Revisar `run_pm_scheduler()`.
- [ ] Revisar botón `action_generate_alerts()`.
- [ ] Probar caso km.
- [ ] Probar caso días.
- [ ] Probar caso horas.
- [ ] Probar vehículo sin equipo asociado.
- [ ] Probar plan sin líneas.

## Si se toca importación manual de ubicaciones técnicas

- [ ] No reintroducir dependencia runtime de `data/technical_locations.csv`.
- [ ] Revisar categorías exactas en `fleet.vehicle.model.category`.
- [ ] Validar códigos únicos para XML IDs automáticos.
- [ ] Revisar creación de XML IDs mediante `_ensure_external_ids()`.
- [ ] No asumir que `post_init_hook` se ejecutará en actualización.

## Pruebas mínimas sugeridas

Después de cada cambio relevante:

1. Actualizar módulo.
2. Abrir menú `Mantención Barca`.
3. Crear/editar ubicación técnica.
4. Crear/editar actividad.
5. Crear plan con línea.
6. Generar aviso manual.
7. Aprobar aviso.
8. Crear OT.
9. Mover OT a etapa cerrada/plegada.
10. Confirmar que aviso pasa a revisión.
11. Cerrar aviso.
12. Verificar actualización de medidores del vehículo.
13. Ejecutar cron manualmente o método `run_pm_scheduler()`.

## Comando tipo para pedir trabajo a Codex

```text
Lee AGENTS.md y docs_codex antes de modificar. Trabaja sobre Odoo 18 Community. No uses modelos obsoletos. Haz cambios mínimos y explícitos. Al final explica archivos modificados, impacto en modelos/vistas/seguridad, y pruebas sugeridas para actualizar el módulo zmm_ajustes.
```
