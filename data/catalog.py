"""French SKU catalog shared across the logistics portfolio."""

SKUS = [
    {"sku": "SKU-001", "name": "Lait demi-écrémé 1L",        "zone": "FRAIS",   "price": 1.05},
    {"sku": "SKU-002", "name": "Yaourt nature x4",            "zone": "FRAIS",   "price": 1.85},
    {"sku": "SKU-003", "name": "Fromage râpé 200g",           "zone": "FRAIS",   "price": 2.40},
    {"sku": "SKU-004", "name": "Beurre doux 250g",            "zone": "FRAIS",   "price": 2.10},
    {"sku": "SKU-005", "name": "Crème fraîche 20cl",          "zone": "FRAIS",   "price": 1.55},
    {"sku": "SKU-006", "name": "Jambon blanc x4",             "zone": "FRAIS",   "price": 3.20},
    {"sku": "SKU-007", "name": "Saucisson sec",               "zone": "FRAIS",   "price": 4.90},
    {"sku": "SKU-008", "name": "Poulet rôti",                 "zone": "FRAIS",   "price": 8.50},
    {"sku": "SKU-009", "name": "Saumon fumé 100g",            "zone": "FRAIS",   "price": 4.30},
    {"sku": "SKU-010", "name": "Œufs frais x6",               "zone": "FRAIS",   "price": 2.05},
    {"sku": "SKU-011", "name": "Glace vanille 1L",            "zone": "SURGELE", "price": 4.20},
    {"sku": "SKU-012", "name": "Pizza surgelée",              "zone": "SURGELE", "price": 3.80},
    {"sku": "SKU-013", "name": "Frites surgelées 1kg",        "zone": "SURGELE", "price": 2.65},
    {"sku": "SKU-014", "name": "Légumes mélangés 750g",       "zone": "SURGELE", "price": 2.40},
    {"sku": "SKU-015", "name": "Filets de poisson",           "zone": "SURGELE", "price": 5.10},
    {"sku": "SKU-016", "name": "Baguette tradition",          "zone": "BOULANGERIE", "price": 1.20},
    {"sku": "SKU-017", "name": "Croissants x6",               "zone": "BOULANGERIE", "price": 3.50},
    {"sku": "SKU-018", "name": "Pain de mie complet",         "zone": "BOULANGERIE", "price": 1.85},
    {"sku": "SKU-019", "name": "Brioche tranchée",            "zone": "BOULANGERIE", "price": 2.40},
    {"sku": "SKU-020", "name": "Pâtes spaghetti 500g",        "zone": "EPICERIE", "price": 1.10},
    {"sku": "SKU-021", "name": "Riz basmati 1kg",             "zone": "EPICERIE", "price": 2.95},
    {"sku": "SKU-022", "name": "Huile d'olive 1L",            "zone": "EPICERIE", "price": 7.80},
    {"sku": "SKU-023", "name": "Sucre en poudre 1kg",         "zone": "EPICERIE", "price": 1.25},
    {"sku": "SKU-024", "name": "Farine T55 1kg",              "zone": "EPICERIE", "price": 1.05},
    {"sku": "SKU-025", "name": "Café moulu 250g",             "zone": "EPICERIE", "price": 4.10},
    {"sku": "SKU-026", "name": "Thé Earl Grey x25",           "zone": "EPICERIE", "price": 3.20},
    {"sku": "SKU-027", "name": "Chocolat noir 100g",          "zone": "EPICERIE", "price": 1.95},
    {"sku": "SKU-028", "name": "Confiture fraise 370g",       "zone": "EPICERIE", "price": 2.65},
    {"sku": "SKU-029", "name": "Biscuits sablés 200g",        "zone": "EPICERIE", "price": 1.80},
    {"sku": "SKU-030", "name": "Céréales chocolat 500g",      "zone": "EPICERIE", "price": 3.40},
    {"sku": "SKU-031", "name": "Eau minérale 6×1.5L",         "zone": "BOISSONS", "price": 2.40},
    {"sku": "SKU-032", "name": "Jus d'orange 1L",             "zone": "BOISSONS", "price": 2.10},
    {"sku": "SKU-033", "name": "Soda cola 1.5L",              "zone": "BOISSONS", "price": 1.85},
    {"sku": "SKU-034", "name": "Bière blonde x6",             "zone": "BOISSONS", "price": 5.40},
    {"sku": "SKU-035", "name": "Vin rouge Bordeaux",          "zone": "BOISSONS", "price": 8.90},
    {"sku": "SKU-036", "name": "Lessive liquide 3L",          "zone": "DROGUERIE", "price": 9.50},
    {"sku": "SKU-037", "name": "Liquide vaisselle 1L",        "zone": "DROGUERIE", "price": 2.80},
    {"sku": "SKU-038", "name": "Papier toilette x12",         "zone": "DROGUERIE", "price": 6.40},
    {"sku": "SKU-039", "name": "Essuie-tout x4",              "zone": "DROGUERIE", "price": 4.20},
    {"sku": "SKU-040", "name": "Dentifrice 75ml",             "zone": "HYGIENE",   "price": 2.45},
    {"sku": "SKU-041", "name": "Shampoing 250ml",             "zone": "HYGIENE",   "price": 3.80},
    {"sku": "SKU-042", "name": "Gel douche 500ml",            "zone": "HYGIENE",   "price": 3.10},
    {"sku": "SKU-043", "name": "Pommes Golden 1kg",           "zone": "FRUITS_LEGUMES", "price": 2.20},
    {"sku": "SKU-044", "name": "Tomates grappe 500g",         "zone": "FRUITS_LEGUMES", "price": 2.80},
    {"sku": "SKU-045", "name": "Bananes 1kg",                 "zone": "FRUITS_LEGUMES", "price": 1.75},
]

ZONES = sorted({s["zone"] for s in SKUS})
ZONE_TO_INT = {z: i for i, z in enumerate(ZONES)}

SUPPLIERS = [
    "Lactalis France", "Danone SA", "Bonduelle Frais", "Findus Surgelés",
    "Boulangerie Paul", "Panzani SA", "Lesieur", "Nestlé France",
    "Coca-Cola Européenne", "Heineken France", "Henkel Hygiène", "Carrefour Logistic",
]


def sku_to_index(sku: str) -> int:
    return int(sku.split("-")[1]) - 1
