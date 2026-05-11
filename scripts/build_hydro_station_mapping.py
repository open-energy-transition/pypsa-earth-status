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

    buses = n.buses[["x", "y"]].rename(columns={"x": "bus_lon", "y": "bus_lat"})
    buses = buses.dropna(subset=["bus_lat", "bus_lon"])
    if buses.empty:
        raise ValueError("No buses with valid coordinates found in the network.")
    kd = KDTree(buses[["bus_lat", "bus_lon"]].values)

    # Flatten station→plant dict into a DataFrame
    pairs = pd.DataFrame(
        [(s, p) for s, plants in station_to_powerplants.items() for p in plants],
        columns=["station_name", "plant_name"],
    )

    # Join plant coordinates; drop_duplicates collapses split entries (e.g. ITT)
    ppl_coords = (
        ppl.drop_duplicates(subset=["Name"])
        .rename(columns={"Name": "plant_name", "lat": "plant_lat", "lon": "plant_lon"})
        [["plant_name", "plant_lat", "plant_lon"]]
    )
    df = pairs.merge(ppl_coords, on="plant_name", how="left")

    missing = df[df["plant_lat"].isna()]
    if not missing.empty:
        logger.warning(
            "The following plants were not found in powerplants.csv and were skipped:\n%s",
            missing[["station_name", "plant_name"]].to_string(index=False),
        )
    df = df.dropna(subset=["plant_lat", "plant_lon"])

    if df.empty:
        raise ValueError(
            "No plants were matched. Check that 'station_to_powerplants' names "
            "exactly match the 'Name' column in powerplants.csv."
        )

    # Batch spatial query — all plants in one KDTree call
    dists, idxs = kd.query(df[["plant_lat", "plant_lon"]].values)

    df["bus_id"] = buses.index[idxs]
    df["bus_lat"] = buses["bus_lat"].values[idxs]
    df["bus_lon"] = buses["bus_lon"].values[idxs]
    df["distance_km"] = np.round(dists * 111.0, 2)

    far = df[df["distance_km"] > 50]
    if not far.empty:
        logger.warning(
            "The following plants mapped to a bus >50 km away — "
            "verify clustering is correct:\n%s",
            far[["station_name", "plant_name", "bus_id", "distance_km"]].to_string(),
        )

    logger.info("Mapped %d plants across %d stations:\n%s", len(df),
                df["station_name"].nunique(),
                df[["station_name", "plant_name", "bus_id", "distance_km"]].to_string(index=False))

    return df[["station_name", "plant_name", "bus_id",
               "plant_lat", "plant_lon", "bus_lat", "bus_lon", "distance_km"]]


if __name__ == "__main__":
    if "snakemake" not in globals():
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
