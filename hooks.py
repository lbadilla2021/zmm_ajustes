import csv
import logging
import os

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def load_technical_locations(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})

    module_path = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(module_path, "data", "technical_locations.csv")

    _logger.info("Iniciando carga de ubicaciones técnicas")
    _logger.info("Archivo CSV detectado en: %s", file_path)

    if not os.path.exists(file_path):
        _logger.warning("Archivo no encontrado: %s", file_path)
    else:
        skipped_rows = 0

        with open(file_path, newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file, delimiter=";")

            for row_number, row in enumerate(reader, start=2):
                categoria = (row.get("CATEGORIA") or "").strip()
                ubicacion = (row.get("UBICACION TECNICA") or "").strip()
                codigo_ubicacion = (row.get("CODIGO UBICACION") or "").strip()
                sububicacion = (row.get("SUB UBICACION") or "").strip()
                codigo_sububicacion = (row.get("CODIGO SUBUBICACION") or "").strip()

                if not categoria or not ubicacion:
                    skipped_rows += 1
                    _logger.warning(
                        "Fila omitida (%s): faltan CATEGORIA o UBICACION TECNICA. Datos: %s",
                        row_number,
                        row,
                    )
                    continue

                try:
                    category = env["fleet.vehicle.model.category"].search(
                        [("name", "=", categoria)],
                        limit=1,
                    )
                    if not category:
                        skipped_rows += 1
                        _logger.warning(
                            "Categoría no encontrada en fila %s: %s", row_number, categoria
                        )
                        continue

                    parent = env["barca.technical.location"].search(
                        [
                            ("name", "=", ubicacion),
                            ("category_id", "=", category.id),
                            ("parent_id", "=", False),
                        ],
                        limit=1,
                    )

                    if not parent:
                        parent = env["barca.technical.location"].create(
                            {
                                "name": ubicacion,
                                "code": codigo_ubicacion,
                                "category_id": category.id,
                                "level": 1,
                            }
                        )
                        _logger.info(
                            "Creación de nodo padre (fila %s): %s", row_number, parent.complete_name
                        )

                    if sububicacion:
                        existing_child = env["barca.technical.location"].search(
                            [
                                ("name", "=", sububicacion),
                                ("category_id", "=", category.id),
                                ("parent_id", "=", parent.id),
                            ],
                            limit=1,
                        )

                        if not existing_child:
                            child = env["barca.technical.location"].create(
                                {
                                    "name": sububicacion,
                                    "code": codigo_sububicacion,
                                    "category_id": category.id,
                                    "parent_id": parent.id,
                                    "level": 2,
                                }
                            )
                            _logger.info(
                                "Creación de nodo hijo (fila %s): %s", row_number, child.complete_name
                            )
                except Exception as error:  # pragma: no cover
                    skipped_rows += 1
                    _logger.error("Error procesando fila %s: %s", row, error)

        if skipped_rows:
            _logger.warning("Carga finalizada con %s filas omitidas.", skipped_rows)
        else:
            _logger.info("Carga finalizada sin filas omitidas.")

    sync_existing_vehicle_equipment(cr, registry)


def sync_existing_vehicle_equipment(cr, registry):
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
