# 00 — Contexto general del módulo

## Propósito

`zmm_ajustes` es un módulo personalizado de Odoo 18 Community para Barca SpA. Su objetivo es crear una capa de mantención de flota y equipos sobre módulos estándar de Odoo, integrando:

- `fleet`
- `hr_fleet`
- `zhr_ajustes`
- `maintenance`
- `stock`
- `mail`
- `web`
- `website`
- `zweb_offline_forms`

El módulo está orientado a gestionar mantención preventiva y correctiva de vehículos/equipos mediante categorías de vehículos, ubicaciones técnicas, actividades, planes preventivos, avisos de mantención, kits/materiales, solicitudes simples, checklist y órdenes de trabajo basadas en `maintenance.request`. Solicitudes y checklist también disponen de formularios web/offline autenticados.

Los documentos principales tienen correlativos independientes: Solicitud de Mantención `SM-*`, Aviso `AVS-*` y Orden de Trabajo `OT-*`. La OT muestra el aviso relacionado como **Aviso de origen**.

## Enfoque funcional

El módulo busca que Barca pueda estructurar su mantenimiento así:

1. Definir categorías de vehículos, por ejemplo camioneta, camión, camión pluma, etc.
2. Definir ubicaciones técnicas por categoría, por ejemplo motor, transmisión, sistema eléctrico, frenos, suspensión.
3. Definir actividades de mantención asociadas a categoría + ubicación técnica.
4. Crear planes de mantención preventiva con triggers por kilómetros, días u horas.
5. Evaluar automáticamente los planes mediante cron o manualmente desde el formulario.
6. Crear solicitudes simples de mantención (`barca.maintenance.request`) cuando un usuario reporta una necesidad.
7. Generar avisos de mantención (`barca.maintenance.alert`) desde solicitudes simples, checklist o planes preventivos.
8. El programador toma el aviso para evaluación, asigna una **Fecha Programada** y genera la OT en etapa **Aprobada**.
9. El Jefe de Taller inicia la primera actividad; el sistema cambia automáticamente la OT a **En progreso**, registra su fecha/hora real de inicio y habilita la ejecución operativa.
10. El programador devuelve la OT a **En progreso** o la cierra como **Cierre Total** / **Cierre Parcial**.
11. Al cierre parcial o total se propone la fecha de salida de taller, se calcula el tiempo fuera de servicio y se cierra automáticamente el aviso asociado.
12. Si el aviso es PM, su cierre actualiza los medidores del vehículo sin retroceder valores.

## Principio de diseño

Este módulo no reemplaza completamente `fleet` ni `maintenance`; los extiende. La lógica propia de Barca vive principalmente en modelos `barca.*`, pero los activos reales siguen conectados con `fleet.vehicle` y `maintenance.equipment`.

## Alcance empresarial vigente

La operación actual se considera monoempresa y corresponde a **Barca SpA**. Aunque la compañía **INDOOR** existe en la base, no se utiliza operativamente. El aislamiento multiempresa completo queda registrado como deuda técnica y debe resolverse antes de activar operaciones para INDOOR u otra compañía; ver `07_riesgos_y_errores_conocidos.md`, punto 9.

## Dependencias declaradas

En `__manifest__.py`:

```python
'depends': [
    'fleet', 'hr_fleet', 'zhr_ajustes', 'maintenance', 'stock', 'mail',
    'web', 'website', 'zweb_offline_forms',
]
```

**Nota:** `purchase` fue eliminado de las dependencias en la revisión de Fase 6 por no tener uso en el código actual.

## Archivos clave

- `models/maintenance_plan.py`: lógica central de planes preventivos y generación de avisos.
- `models/maintenance_alert.py`: flujo de avisos, estados, fecha programada, creación de OT y cierre.
- `models/maintenance_request_simple.py`: solicitud simple de mantención que puede originar un aviso.
- `models/maintenance_checklist.py`: checklist operativo, catálogo de ítems y generación automática de avisos ante respuestas No.
- `models/maintenance_request.py`: extensión de la OT estándar, actividades, materiales, revisión, cierres y fechas de taller.
- `controllers/maintenance_request_website.py`: portal web/offline de Solicitud de Mantención.
- `controllers/checklist.py`: portal web/offline de Checklist.
- `security/record_rules.xml`: propiedad de solicitudes/checklists del Conductor y sus líneas.
- `models/fleet_vehicle.py`: campos extendidos de vehículos, detección de seguro, alertas por cambios documentales/vencimientos y sincronización con equipos.
- `models/fleet_alert_rule.py`: reglas/listas de distribución para alertas de flotilla.
- `models/fleet_vehicle_log_contract.py`: adjuntos múltiples para contratos de flotilla.
- `models/maintenance_equipment.py`: vínculo entre equipo de mantenimiento y vehículo.
- `models/technical_location.py`: árbol de ubicaciones técnicas.
- `models/maintenance_activity.py`: catálogo de actividades por categoría y ubicación, con propuesta maestra de materiales/repuestos/kits.
- `models/maintenance_plan_line.py`: actividades incluidas en cada plan y productos/repuestos/kits asociados a cada actividad.
- `models/maintenance_kit.py`: kits de materiales asociados a mantención en lógica legada.
- `hooks.py`: sincronización inicial de equipos de mantenimiento para vehículos existentes. Las ubicaciones técnicas se crean o importan manualmente después de instalar el módulo.

## Criterio para Codex

Cuando se trabaje en este módulo, no basta con modificar un archivo aislado. Cada cambio debe revisar impacto en:

- Python models.
- XML views.
- Seguridad y grupos.
- Datos del módulo / hooks.
- Cron.
- Menús y acciones.
- Compatibilidad Odoo 18.
- Actualización del módulo en una base existente.
