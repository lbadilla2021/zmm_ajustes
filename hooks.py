import csv
import os

from odoo import SUPERUSER_ID, api


def load_technical_locations(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})

    module_path = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(module_path, "data", "technical_locations.csv")

    if not os.path.exists(file_path):
        return

    with open(file_path, newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file, delimiter=";")

        for row in reader:
            categoria = (row.get("CATEGORIA") or "").strip()
            ubicacion = (row.get("UBICACION TECNICA") or "").strip()
            codigo_ubicacion = (row.get("CODIGO UBICACION") or "").strip()
            sububicacion = (row.get("SUB UBICACION") or "").strip()
            codigo_sububicacion = (row.get("CODIGO SUBUBICACION") or "").strip()

            if not categoria or not ubicacion:
                continue

            category = env["fleet.vehicle.model.category"].search(
                [("name", "=", categoria)],
                limit=1,
            )
            if not category:
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
                    env["barca.technical.location"].create(
                        {
                            "name": sububicacion,
                            "code": codigo_sububicacion,
                            "category_id": category.id,
                            "parent_id": parent.id,
                            "level": 2,
                        }
                    )
