"""Veiligheidsregio's, diensten and police units shared by the feed sources."""
from __future__ import annotations

REGIONS = {
    "1": "Amsterdam-Amstelland", "2": "Groningen", "3": "Noord- en Oost-Gelderland",
    "4": "Zaanstreek-Waterland", "5": "Hollands Midden", "6": "Brabant-Noord",
    "7": "Friesland", "8": "Gelderland-Midden", "9": "Kennemerland",
    "10": "Rotterdam-Rijnmond", "11": "Brabant-Zuidoost", "12": "Drenthe",
    "13": "Gelderland-Zuid", "14": "Zuid-Holland-Zuid", "15": "Limburg-Noord",
    "17": "IJsselland", "18": "Utrecht", "19": "Gooi en Vechtstreek", "20": "Zeeland",
    "21": "Zuid-Limburg", "23": "Twente", "24": "Noord-Holland-Noord", "25": "Haaglanden",
    "26": "Midden- en West-Brabant", "27": "Flevoland",
}
SERVICES = {"1": "Politiediensten", "2": "Brandweerdiensten", "3": "Ambulancediensten", "4": "KNRM", "5": "Lifeliner", "7": "DARES"}


# Police alerts carry a police unit ("Eenheid Limburg") instead of a
# veiligheidsregio, under the id of one of its regions (Limburg = 21). Map each
# unit to all veiligheidsregio's it covers, so region filters work for police.
POLICE_UNITS = {
    "noord-nederland": ["2", "7", "12"],
    "oost-nederland": ["3", "8", "13", "17", "23"],
    "midden-nederland": ["18", "19", "27"],
    "noord-holland": ["4", "9", "24"],
    "amsterdam": ["1"],
    "den haag": ["5", "25"],
    "rotterdam": ["10", "14"],
    "zeeland-west-brabant": ["20", "26"],
    "oost-brabant": ["6", "11"],
    "limburg": ["15", "21"],
}


def police_unit_regions(region_text: str) -> list[str] | None:
    """Veiligheidsregio ids covered by a police unit name, or None if not a unit."""
    text = region_text.strip().lower()
    if not text.startswith("eenheid"):
        return None
    return POLICE_UNITS.get(text.removeprefix("eenheid").strip())
