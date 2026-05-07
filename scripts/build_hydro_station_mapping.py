# SPDX-FileCopyrightText:  PyPSA-Earth and PyPSA-Eur Authors

# SPDX-License-Identifier: AGPL-3.0-or-later

# -*- coding: utf-8 -*-
"""
build_hydro_station_mapping.py
==============================
Builds a station → bus lookup table by spatially joining each reference
station's powerplant coordinates against the clustered network buses.

Because clustering can merge several physical plants into one bus, the output
table has one row per (station, plant) pair, recording the matched bus ID.
Downstream scripts deduplicate on bus_id before summing generation so no bus
is counted twice for the same station.
"""

import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pypsa
from scipy.spatial import KDTree
from helpers import configure_logging, mock_snakemake

logger = logging.getLogger(__name__)


def build_mapping(
    powerplants_path: Path,
    network_path: Path,
    station_to_powerplants: dict,
) -> pd.DataFrame:
    """
    Return a DataFrame with columns:
        station_name | plant_name | bus_id | plant_lat | plant_lon
                     | bus_lat   | bus_lon | distance_km
    """
    ppl = pd.read_csv(powerplants_path)
    n = pypsa.Network(str(network_path))

    # Bus coordinates — PyPSA stores lon in x, lat in y
    buses = n.buses[["x", "y"]].rename(columns={"x": "bus_lon", "y": "bus_lat"})
    buses = buses.dropna(subset=["bus_lat", "bus_lon"])
    if buses.empty:
        raise ValueError("No buses with valid coordinates found in the network.")
    bus_coords = buses[["bus_lat", "bus_lon"]].values  # (N, 2)
    kd = KDTree(bus_coords)

    rows = []
    for station, plant_names in station_to_powerplants.items():
        for plant_name in plant_names:
            matches = ppl[ppl["Name"] == plant_name]
            if matches.empty:
                logger.warning(
                    "Plant '%s' (station '%s') not found in powerplants.csv — skipping.",
                    plant_name, station,
                )
                continue

            # Use the first row if there are duplicates (e.g. ITT split entries)
            row = matches.iloc[0]
            plant_lat, plant_lon = row["lat"], row["lon"]

            dist, idx = kd.query([plant_lat, plant_lon])
            matched_bus = buses.index[idx]
            bus_row = buses.iloc[idx]

            # Approximate km distance (1° ≈ 111 km)
            dist_km = dist * 111.0

            rows.append(
                {
                    "station_name": station,
                    "plant_name": plant_name,
                    "bus_id": matched_bus,
                    "plant_lat": plant_lat,
                    "plant_lon": plant_lon,
                    "bus_lat": bus_row["bus_lat"],
                    "bus_lon": bus_row["bus_lon"],
                    "distance_km": round(dist_km, 2),
                }
            )
            logger.info(
                "  %s / %-25s → bus %-6s  (%.1f km)",
                station, plant_name, matched_bus, dist_km,
            )

    df = pd.DataFrame(rows)

    if df.empty:
        raise ValueError(
            "No plants were matched. Check that 'station_to_powerplants' names "
            "exactly match the 'Name' column in powerplants.csv."
        )

    # Warn if any plant mapped very far from a bus (likely a clustering artefact)
    far = df[df["distance_km"] > 50]
    if not far.empty:
        logger.warning(
            "The following plants mapped to a bus >50 km away — "
            "verify clustering is correct:\n%s",
            far[["station_name", "plant_name", "bus_id", "distance_km"]].to_string(),
        )

    return df


if "snakemake" not in dir():
    snakemake = mock_snakemake(
        "build_hydro_station_mapping",
        run="validation_dispatch_zambia_2024",
    )

configure_logging(snakemake)

mapping = build_mapping(
    powerplants_path=Path(snakemake.input.powerplants),
    network_path=Path(snakemake.input.network),
    station_to_powerplants=snakemake.params.station_to_powerplants,
)

out_path = Path(snakemake.output.mapping)
out_path.parent.mkdir(parents=True, exist_ok=True)
mapping.to_csv(out_path, index=False)
logger.info("Saved hydro station mapping → %s", out_path)
