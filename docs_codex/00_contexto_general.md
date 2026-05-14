# 00 — Contexto general del módulo

## Propósito

`zmm_ajustes` es un módulo personalizado de Odoo 18 Community para Barca SpA. Su objetivo es crear una capa de mantención de flota y equipos sobre módulos estándar de Odoo, integrando:

- `fleet`
- `hr_fleet`
- `maintenance`
- `stock`
- `purchase`
- `mail`

El módulo está orientado a gestionar mantención preventiva y correctiva de vehículos/equipos mediante categorías de vehículos, ubicaciones técnicas, actividades, planes preventivos, avisos de mantención, kits/materiales y solicitudes simples de mantención, avisos técnicos y órdenes de trabajo basadas en `maintenance.request`.

## Enfoque funcional

El módulo busca que Barca pueda estructurar su mantenimiento así:

1. Definir categorías de vehículos, por ejemplo camioneta, camión, camión pluma, etc.
2. Definir ubicaciones técnicas por categoría, por ejemplo motor, transmisión, sistema eléctrico, frenos, suspensión.
3. Definir actividades de mantención asociadas a categoría + ubicación técnica.
4. Crear planes de mantención preventiva con triggers por kilómetros, días u horas.
5. Evaluar automáticamente los planes mediante cron o manualmente desde el formulario.
6. Crear solicitudes simples de mantención (`barca.maintenance.request`) cuando un usuario reporta una necesidad.
7. Generar avisos de mantención (`barca.maintenance.alert`) desde solicitudes simples, checklist o planes preventivos.
8. Aprobar/rechazar avisos y crear órdenes de trabajo (`maintenance.request`) desde avisos aprobados.
9. Actualizar medidores del vehículo al cerrar avisos PM.

## Principio de diseño

Este módulo no reemplaza completamente `fleet` ni `maintenance`; los extiende. La lógica propia de Barca vive principalmente en modelos `barca.*`, pero los activos reales siguen conectados con `fleet.vehicle` y `maintenance.equipment`.

## Dependencias declaradas

En `__manifest__.py`:

```python
'depends': ['fleet', 'hr_fleet', 'maintenance', 'stock', 'purchase', 'mail']
```

Esto significa que cualquier modificación debe considerar compatibilidad con esos módulos estándar.

## Archivos clave

- `models/maintenance_plan.py`: lógica central de planes preventivos y generación de avisos.
- `models/maintenance_alert.py`: flujo de avisos, estados, creación de OT y cierre.
- `models/maintenance_request_simple.py`: solicitud simple de mantención que puede originar un aviso.
- `models/fleet_vehicle.py`: campos extendidos de vehículos, detección de seguro, alertas por cambios documentales y sincronización con equipos.
- `models/fleet_alert_rule.py`: reglas/listas de distribución para alertas de flotilla.
- `models/fleet_vehicle_log_contract.py`: adjuntos múltiples para contratos de flotilla.
- `models/maintenance_equipment.py`: vínculo entre equipo de mantenimiento y vehículo.
- `models/technical_location.py`: árbol de ubicaciones técnicas.
- `models/maintenance_activity.py`: catálogo de actividades por categoría y ubicación.
- `models/maintenance_plan_line.py`: actividades incluidas en cada plan.
- `models/maintenance_kit.py`: kits de materiales asociados a mantención.
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
