"""Pre-generated datasets — lazily cached singletons."""
from __future__ import annotations

from typing import Dict

import pandas as pd

from data import generator

_CACHE: Dict[str, pd.DataFrame] = {}


def operators_df() -> pd.DataFrame:
    if "operators" not in _CACHE:
        _CACHE["operators"] = generator.generate_operators()
    return _CACHE["operators"].copy()


def inventory_df() -> pd.DataFrame:
    if "inventory" not in _CACHE:
        _CACHE["inventory"] = generator.generate_inventory()
    return _CACHE["inventory"].copy()


def routes_df() -> pd.DataFrame:
    if "routes" not in _CACHE:
        _CACHE["routes"] = generator.generate_routes()
    return _CACHE["routes"].copy()


def deliveries_df() -> pd.DataFrame:
    if "deliveries" not in _CACHE:
        _CACHE["deliveries"] = generator.generate_deliveries()
    return _CACHE["deliveries"].copy()


def all_data() -> Dict[str, pd.DataFrame]:
    return {
        "operators": operators_df(),
        "inventory": inventory_df(),
        "routes": routes_df(),
        "deliveries": deliveries_df(),
    }
