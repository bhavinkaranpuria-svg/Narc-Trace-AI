"""
Kit profile registry.

Each kit profile describes the expected calibrated colour response of a given
field colorimetric test kit: a reference point in CIELAB space for a
"negative" reaction and one (or more) for a "positive" reaction, plus the
distance thresholds used to decide when a reading is too ambiguous to call.

IMPORTANT — these Lab reference points are DEMO PLACEHOLDER values, not
validated laboratory calibration data. In a real deployment these would come
from controlled reagent trials run against each NCB-approved kit batch
(see feature #8/#23 in the design notes — kit-batch colour drift monitoring).
Swap the values in KIT_PROFILES for validated figures before this touches a
real chain of custody.
"""
from dataclasses import dataclass, field
from typing import Dict, Tuple


@dataclass
class KitProfile:
    id: str
    name: str
    description: str
    negative_lab: Tuple[float, float, float]
    positive_lab: Tuple[float, float, float]
    # Below this Delta-E from a reference point, a match counts as "strong"
    strong_match_deltae: float = 12.0
    # Above this Delta-E from BOTH reference points, no reaction is recognised at all
    no_match_deltae: float = 42.0
    # Minimum normalised margin between the two candidate distances to avoid "inconclusive"
    min_confidence_margin: float = 0.22


KIT_PROFILES: Dict[str, KitProfile] = {
    "std-narcotic": KitProfile(
        id="std-narcotic",
        name="Standard Narcotic Kit",
        description="General-purpose presumptive colour kit for common narcotic classes.",
        negative_lab=(62.0, 2.0, 4.0),      # pale / straw, near-neutral
        positive_lab=(38.0, 34.0, -28.0),   # strong violet-blue reaction
    ),
    "precursor": KitProfile(
        id="precursor",
        name="Precursor Chemical Kit",
        description="Presumptive kit for precursor-chemical screening.",
        negative_lab=(58.0, -3.0, 6.0),
        positive_lab=(46.0, 46.0, 30.0),    # orange-red reaction
    ),
    "ketamine": KitProfile(
        id="ketamine",
        name="Ketamine Kit",
        description="Presumptive kit for ketamine-class substances.",
        negative_lab=(64.0, 1.0, 2.0),
        positive_lab=(30.0, 12.0, -40.0),   # deep blue reaction
    ),
}


def get_kit(kit_id: str) -> KitProfile:
    if kit_id not in KIT_PROFILES:
        raise KeyError(f"Unknown kit_id '{kit_id}'")
    return KIT_PROFILES[kit_id]


def list_kits():
    return [
        {
            "id": k.id,
            "name": k.name,
            "description": k.description,
        }
        for k in KIT_PROFILES.values()
    ]
