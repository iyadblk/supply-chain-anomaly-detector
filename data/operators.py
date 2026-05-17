"""Operator roster shared across the logistics portfolio."""

OPERATORS = [
    {"id": "OP-01", "name": "Lucas Martin",       "baseline_picks": 58, "baseline_error": 1.0},
    {"id": "OP-02", "name": "Emma Bernard",       "baseline_picks": 62, "baseline_error": 0.8},
    {"id": "OP-03", "name": "Hugo Dubois",        "baseline_picks": 55, "baseline_error": 1.4},
    {"id": "OP-04", "name": "Léa Thomas",         "baseline_picks": 60, "baseline_error": 1.1},
    {"id": "OP-05", "name": "Nathan Robert",      "baseline_picks": 52, "baseline_error": 1.6},
    {"id": "OP-06", "name": "Chloé Petit",        "baseline_picks": 64, "baseline_error": 0.7},
    {"id": "OP-07", "name": "Louis Richard",      "baseline_picks": 56, "baseline_error": 1.2},
    {"id": "OP-08", "name": "Manon Durand",       "baseline_picks": 59, "baseline_error": 1.0},
    {"id": "OP-09", "name": "Jules Moreau",       "baseline_picks": 53, "baseline_error": 1.5},
    {"id": "OP-10", "name": "Camille Laurent",    "baseline_picks": 61, "baseline_error": 0.9},
    {"id": "OP-11", "name": "Adam Simon",         "baseline_picks": 57, "baseline_error": 1.1},
    {"id": "OP-12", "name": "Sarah Michel",       "baseline_picks": 60, "baseline_error": 1.0},
    {"id": "OP-13", "name": "Raphaël Leroy",      "baseline_picks": 54, "baseline_error": 1.3},
    {"id": "OP-14", "name": "Inès Roux",          "baseline_picks": 63, "baseline_error": 0.8},
    {"id": "OP-15", "name": "Théo David",         "baseline_picks": 55, "baseline_error": 1.4},
    {"id": "OP-16", "name": "Jade Bertrand",      "baseline_picks": 58, "baseline_error": 1.1},
    {"id": "OP-17", "name": "Gabriel Morel",      "baseline_picks": 56, "baseline_error": 1.2},
    {"id": "OP-18", "name": "Louise Fournier",    "baseline_picks": 62, "baseline_error": 0.9},
    {"id": "OP-19", "name": "Arthur Girard",      "baseline_picks": 51, "baseline_error": 1.7},
    {"id": "OP-20", "name": "Alice Bonnet",       "baseline_picks": 59, "baseline_error": 1.0},
]


def operator_index(op_id: str) -> int:
    return int(op_id.split("-")[1]) - 1
