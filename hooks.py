import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def sync_existing_vehicle_equipment(cr, registry):
    """Create missing maintenance.equipment records for existing vehicles.

    Technical locations are no longer imported from a bundled CSV during module
    installation. They must be created or imported manually after installing the
    module. The post-init hook is kept only for vehicle/equipment consistency.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    vehicles = env["fleet.vehicle"].search([])
    created_count = 0

    for vehicle in vehicles:
        exists = env["maintenance.equipment"].search_count(
            [("vehicle_id", "=", vehicle.id)]
        )
        if exists:
            continue

        env["maintenance.equipment"].create(
            {
                "name": vehicle.name,
                "vehicle_id": vehicle.id,
            }
        )
        created_count += 1

    _logger.info(
        "Sincronización de maintenance.equipment finalizada. "
        "Vehículos revisados: %s, equipos creados: %s",
        len(vehicles),
        created_count,
    )
