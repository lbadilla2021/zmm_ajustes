{
    "name": "Barca Mantenimiento",
    "version": "1.0",
    "summary": "Módulo de mantención de flota Barca SpA",
    "category": "Operations",
    "depends": [
        "fleet",
        "maintenance",
        "stock",
        "purchase",
        "mail",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/base_views.xml",
        "data/cron.xml",
    ],
    "installable": True,
    "application": True,
}
