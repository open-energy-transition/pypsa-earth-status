# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText:  PyPSA-Earth and PyPSA-Eur Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

# -*- coding: utf-8 -*-

"""
Inflow Validation Script for PyPSA-Zambia
==========================================
Validates hydropower inflow profiles by cross-comparing three data sources:
  - GRDC (Global Runoff Data Centre) observed streamflow
  - GloFAS (Global Flood Awareness System) reanalysis discharge
  - atlite-derived inflow profiles (from profile_hydro.nc)

"""

import logging
import sys
from pathlib import Path

import matplotlib
import yaml

matplotlib.use("Agg")

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xarray as xr
from matplotlib.backends.backend_pdf import PdfPages

logger = logging.getLogger(__name__)


def truncate_colormap(
    cmap_name: str, minval: float = 0.0, maxval: float = 1.0, n: int = 256
):
    """Return a sub-range slice of an existing matplotlib colormap."""
    cmap = plt.get_cmap(cmap_name)
    new_colors = cmap(np.linspace(minval, maxval, n))
    return mcolors.LinearSegmentedColormap.from_list(
        f"trunc({cmap_name},{minval:.2f},{maxval:.2f})", new_colors
    )


def extract_grdc_ts(grdc_ds: xr.Dataset, station_name: str) -> xr.DataArray:
    """Return the runoff_mean time-series for a single GRDC station."""
    return (
        grdc_ds["runoff_mean"]
        .where(grdc_ds["station_name"] == station_name, drop=True)
        .isel(id=0)
    )


def extract_grdc_year(grdc_station_ds: xr.Dataset, year: int) -> xr.Dataset:
    """Subset a station dataset to a single calendar year."""
    return grdc_station_ds.where(
        (grdc_station_ds.time.dt.year >= year) & (grdc_station_ds.time.dt.year <= year),
        drop=True,
    )


def subset_grdc_by_bbox(
    grdc_ds: xr.Dataset, lat: float, lon: float, dx: float = 1.0
) -> xr.Dataset:
    """Return GRDC stations within ±dx degrees of (lat, lon)."""
    return grdc_ds.where(
        (grdc_ds["geo_y"] > lat - dx)
        & (grdc_ds["geo_y"] < lat + dx)
        & (grdc_ds["geo_x"] > lon - dx)
        & (grdc_ds["geo_x"] < lon + dx),
        drop=True,
    )


def extract_glofas_loc(
    glofas_ds: xr.Dataset, lat: float, lon: float, dx: float = 0.05
) -> xr.Dataset:
    """Return GloFAS cells within ±dx degrees of (lat, lon)."""
    return glofas_ds.where(
        (glofas_ds["latitude"] > lat - dx)
        & (glofas_ds["latitude"] < lat + dx)
        & (glofas_ds["longitude"] > lon - dx)
        & (glofas_ds["longitude"] < lon + dx),
        drop=True,
    )


def plot_grdc_timeseries(grdc_ds: xr.Dataset, output_pdf: Path) -> None:
    """Write one page per GRDC station into a multi-page PDF."""
    station_names = grdc_ds["station_name"].values.tolist()
    output_pdf.parent.mkdir(parents=True, exist_ok=True)

    with PdfPages(output_pdf) as pdf:
        for st in station_names:
            fig, ax = plt.subplots(figsize=(8, 4))
            extract_grdc_ts(grdc_ds, st).plot(ax=ax)
            ax.set_title(st)
            pdf.savefig(fig)
            plt.close(fig)

    logger.info("Saved GRDC time-series PDF → %s", output_pdf)


def plot_spatial_map(
    glofas_2013: xr.Dataset,
    grdc_ds: xr.Dataset,
    ppl_hydro_df: pd.DataFrame,
    ppl_hydro_selected_df: pd.DataFrame,
    output_png: Path,
) -> None:
    """Map GloFAS mean discharge with GRDC stations and hydro plant locations."""
    cmap_blue_ocean = truncate_colormap("ocean_r", minval=0.05, maxval=0.75)
    output_png.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(7, 5))
    glofas_2013["dis24"].mean(dim=["valid_time"]).plot(
        ax=ax, cmap=cmap_blue_ocean, alpha=1
    )
    ax.scatter(
        grdc_ds["geo_x"].values,
        grdc_ds["geo_y"].values,
        marker="o",
        s=20,
        facecolor="lightgreen",
        edgecolor="darkgreen",
        alpha=0.5,
        label="GRDC",
    )
    ax.scatter(
        ppl_hydro_df["lon"],
        ppl_hydro_df["lat"],
        marker="o",
        s=20,
        facecolor="cornflowerblue",
        edgecolor="blue",
        alpha=0.75,
        label="Hydro generators",
    )
    ax.scatter(
        ppl_hydro_selected_df["lon"],
        ppl_hydro_selected_df["lat"],
        marker="o",
        s=20,
        facecolor="coral",
        edgecolor="darkred",
        alpha=0.75,
        label="Selected hydro generators",
    )
    ax.legend()
    ax.set_title("Hydropower spatial overview — Zambia")
    fig.savefig(output_png, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Saved spatial map → %s", output_png)


def plot_grdc_vs_glofas(
    grdc_station_ds: xr.Dataset,
    glofas_2001_loc: xr.Dataset,
    glofas_2002_loc: xr.Dataset,
    output_pdf: Path,
) -> None:
    """Two-page PDF comparing GRDC and GloFAS discharge for 2001 and 2002."""
    output_pdf.parent.mkdir(parents=True, exist_ok=True)

    grdc_2001 = extract_grdc_year(grdc_station_ds, 2001)
    grdc_2002 = extract_grdc_year(grdc_station_ds, 2002)

    with PdfPages(output_pdf) as pdf:
        for year, grdc_yr, glofas_yr in [
            (2001, grdc_2001, glofas_2001_loc),
            (2002, grdc_2002, glofas_2002_loc),
        ]:
            fig, ax = plt.subplots(figsize=(7, 5))
            (
                glofas_yr.mean(dim=["latitude", "longitude"])["dis24"].plot(
                    ax=ax, color="cornflowerblue", label="GloFAS"
                )
            )
            grdc_yr["runoff_mean"].plot(ax=ax, color="darkblue", label="GRDC")
            ax.set_title(f"GRDC vs GloFAS — {year}")
            ax.legend()
            pdf.savefig(fig)
            plt.close(fig)

    logger.info("Saved GRDC vs GloFAS PDF → %s", output_pdf)


def plot_glofas_vs_atlite(
    hydro_ds: xr.Dataset,
    pl_idx: int,
    glofas_2013_loc: xr.Dataset,
    k_scale: float,
    output_png: Path,
) -> None:
    """Compare scaled atlite inflow (hourly, daily, monthly) to GloFAS 2013."""
    hydro_plant = hydro_ds.where(hydro_ds["plant"] == pl_idx, drop=True)
    hydro_daily = hydro_plant.resample(time="1D").mean()
    hydro_monthly = hydro_plant.resample(time="1ME").mean()
    glofas_monthly = glofas_2013_loc.resample(valid_time="1ME").mean()

    # Log the auto-computed scaling ratio for reference
    mean_glofas = (
        glofas_2013_loc.mean(dim=["latitude", "longitude"])["dis24"]
        .mean()
        .values.item()
    )
    mean_atlite = hydro_monthly["inflow"].mean().values.item()
    ratio = mean_glofas / mean_atlite if mean_atlite else float("nan")
    logger.info(
        "GloFAS/atlite mean ratio for plant %d: %.2f  (using k_scale=%.1f)",
        pl_idx,
        ratio,
        k_scale,
    )

    output_png.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(7, 5))
    (k_scale * hydro_plant["inflow"]).plot(
        ax=ax, color="coral", label="atlite (hourly)", alpha=0.5
    )
    (k_scale * hydro_daily["inflow"]).plot(ax=ax, color="red", label="atlite (daily)")
    (k_scale * hydro_monthly["inflow"]).plot(
        ax=ax, color="darkred", label="atlite (monthly)"
    )
    (
        glofas_2013_loc.mean(dim=["latitude", "longitude"])["dis24"].plot(
            ax=ax, color="cornflowerblue", label="GloFAS"
        )
    )
    (
        glofas_monthly.mean(dim=["latitude", "longitude"])["dis24"].plot(
            ax=ax, color="darkblue", label="GloFAS (monthly)"
        )
    )
    ax.set_title(f"GloFAS vs atlite inflow — plant index {pl_idx}")
    ax.legend()
    fig.savefig(output_png, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Saved GloFAS vs atlite plot → %s", output_png)


def main(
    powerplants_path: Path,
    hydro_profile_path: Path,
    grdc_path: Path,
    glofas_2001_path: Path,
    glofas_2002_path: Path,
    glofas_2013_path: Path,
    out_grdc_ts_pdf: Path,
    out_spatial_png: Path,
    out_grdc_vs_glofas_pdf: Path,
    out_glofas_vs_atlite_png: Path,
    grdc_station: str,
    glofas_dx: float,
    grdc_dx: float,
    k_scale: float,
    ppl_bbox: dict,
    validation_ppl_idx: int,
) -> None:

    logger.info("Loading power plant data from %s", powerplants_path)
    ppl_df = pd.read_csv(powerplants_path)
    ppl_hydro_df = ppl_df.query("Fueltype=='Hydro'").reset_index(drop=True)
    ppl_hydro_selected_df = ppl_hydro_df.query(
        f"(lat>{ppl_bbox['lat_min']})&(lat<{ppl_bbox['lat_max']})"
        f"&(lon>{ppl_bbox['lon_min']})&(lon<{ppl_bbox['lon_max']})"
    )[["Name", "lat", "lon", "Capacity"]]
    logger.info(
        "Found %d hydro plants (%d selected in bbox)",
        len(ppl_hydro_df),
        len(ppl_hydro_selected_df),
    )

    logger.info("Loading GRDC dataset from %s", grdc_path)
    grdc_ds = xr.open_dataset(grdc_path)
    logger.info("GRDC stations: %s", grdc_ds["station_name"].values.tolist())

    # 2a. Time-series PDF for all stations
    plot_grdc_timeseries(grdc_ds, out_grdc_ts_pdf)

    # 2b. Subset to the validation plant's neighbourhood
    val_lat = ppl_hydro_df.iloc[validation_ppl_idx]["lat"]
    val_lon = ppl_hydro_df.iloc[validation_ppl_idx]["lon"]
    logger.info(
        "Validation plant %d location: lat=%.4f  lon=%.4f",
        validation_ppl_idx,
        val_lat,
        val_lon,
    )
    grdc_nearby = subset_grdc_by_bbox(grdc_ds, val_lat, val_lon, dx=grdc_dx)
    grdc_station_ds = grdc_nearby.where(
        grdc_nearby["station_name"] == grdc_station, drop=True
    )

    logger.info("Loading GloFAS datasets")
    glofas_2001 = xr.open_dataset(glofas_2001_path)
    glofas_2002 = xr.open_dataset(glofas_2002_path)
    glofas_2013 = xr.open_dataset(glofas_2013_path)

    plot_spatial_map(
        glofas_2013,
        grdc_ds,
        ppl_hydro_df,
        ppl_hydro_selected_df,
        out_spatial_png,
    )

    logger.info("Loading atlite hydro profile from %s", hydro_profile_path)
    hydro_ds = xr.open_dataset(hydro_profile_path)
    ppl_hydro_idx_list = hydro_ds["plant"].values.tolist()
    pl_idx = ppl_hydro_idx_list[validation_ppl_idx]
    logger.info("Plant index for validation: %s", pl_idx)

    glofas_2001_loc = extract_glofas_loc(glofas_2001, val_lat, val_lon, dx=glofas_dx)
    glofas_2002_loc = extract_glofas_loc(glofas_2002, val_lat, val_lon, dx=glofas_dx)
    plot_grdc_vs_glofas(
        grdc_station_ds,
        glofas_2001_loc,
        glofas_2002_loc,
        out_grdc_vs_glofas_pdf,
    )

    glofas_2013_loc = extract_glofas_loc(glofas_2013, val_lat, val_lon, dx=glofas_dx)
    plot_glofas_vs_atlite(
        hydro_ds,
        pl_idx,
        glofas_2013_loc,
        k_scale,
        out_glofas_vs_atlite_png,
    )

    logger.info("Inflow validation complete.")


if __name__ == "__main__":

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    try:

        if snakemake.log:
            fh = logging.FileHandler(snakemake.log[0])
            fh.setFormatter(
                logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
            )
            logging.getLogger().addHandler(fh)

        main(
            powerplants_path=Path(snakemake.input.powerplants),
            hydro_profile_path=Path(snakemake.input.hydro_profile),
            grdc_path=Path(snakemake.input.grdc),
            glofas_2001_path=Path(snakemake.input.glofas_2001),
            glofas_2002_path=Path(snakemake.input.glofas_2002),
            glofas_2013_path=Path(snakemake.input.glofas_2013),
            out_grdc_ts_pdf=Path(snakemake.output.grdc_ts_pdf),
            out_spatial_png=Path(snakemake.output.spatial_map_png),
            out_grdc_vs_glofas_pdf=Path(snakemake.output.grdc_vs_glofas),
            out_glofas_vs_atlite_png=Path(snakemake.output.glofas_vs_atlite),
            grdc_station=snakemake.params.grdc_station,
            glofas_dx=snakemake.params.glofas_dx,
            grdc_dx=snakemake.params.grdc_dx,
            k_scale=snakemake.params.k_scale,
            ppl_bbox=snakemake.params.ppl_bbox,
            validation_ppl_idx=snakemake.params.validation_ppl_idx,
        )

    except NameError:

        import argparse

        _project_root = Path(__file__).parent.parent
        _workflow_dir = _project_root / "workflows" / "pypsa-earth"
        _cfg = yaml.safe_load((_project_root / "config.yaml").read_text())
        _iv = _cfg.get("inflow_validation", {})
        _run = _iv.get("run", "")
        _bbox = _iv.get("ppl_bbox", {})
        _res = _workflow_dir / "resources" / _run
        _runoff = _workflow_dir / "runoff"
        _out = _project_root / "results" / _run / "inflow_validation"

        parser = argparse.ArgumentParser(
            description="Inflow validation — standalone mode"
        )
        parser.add_argument("--powerplants", default=str(_res / "powerplants.csv"))
        parser.add_argument(
            "--hydro-profile",
            default=str(_res / "renewable_profiles" / "profile_hydro.nc"),
        )
        parser.add_argument("--grdc", default=str(_runoff / "GRDC" / "GRDC-Daily.nc"))
        parser.add_argument(
            "--glofas-2001", default=str(_runoff / "GloFAS" / "zm-2001-glofas.nc")
        )
        parser.add_argument(
            "--glofas-2002", default=str(_runoff / "GloFAS" / "zm-2002-glofas.nc")
        )
        parser.add_argument(
            "--glofas-2013", default=str(_runoff / "GloFAS" / "zm-2013-glofas.nc")
        )
        parser.add_argument(
            "--out-grdc-ts-pdf", default=str(_out / "grdc_timeseries.pdf")
        )
        parser.add_argument(
            "--out-spatial-png", default=str(_out / "spatial_hydro_map.png")
        )
        parser.add_argument(
            "--out-grdc-vs-glofas-pdf", default=str(_out / "grdc_vs_glofas.pdf")
        )
        parser.add_argument(
            "--out-glofas-vs-atlite-png", default=str(_out / "glofas_vs_atlite.png")
        )
        parser.add_argument(
            "--grdc-station",
            default=_iv.get("grdc_station", "KAFUE HOOK BRIDGE (60334669)"),
        )
        parser.add_argument(
            "--glofas-dx", type=float, default=_iv.get("glofas_dx", 0.05)
        )
        parser.add_argument("--grdc-dx", type=float, default=_iv.get("grdc_dx", 1.0))
        parser.add_argument("--k-scale", type=float, default=_iv.get("k_scale", 8.5))
        parser.add_argument(
            "--lat-min", type=float, default=_bbox.get("lat_min", -17.0)
        )
        parser.add_argument(
            "--lat-max", type=float, default=_bbox.get("lat_max", -15.5)
        )
        parser.add_argument("--lon-min", type=float, default=_bbox.get("lon_min", 28.0))
        parser.add_argument("--lon-max", type=float, default=_bbox.get("lon_max", 29.0))
        parser.add_argument(
            "--validation-ppl-idx", type=int, default=_iv.get("validation_ppl_idx", 0)
        )
        args = parser.parse_args()

        Path(args.out_grdc_ts_pdf).parent.mkdir(parents=True, exist_ok=True)

        main(
            powerplants_path=Path(args.powerplants),
            hydro_profile_path=Path(args.hydro_profile),
            grdc_path=Path(args.grdc),
            glofas_2001_path=Path(args.glofas_2001),
            glofas_2002_path=Path(args.glofas_2002),
            glofas_2013_path=Path(args.glofas_2013),
            out_grdc_ts_pdf=Path(args.out_grdc_ts_pdf),
            out_spatial_png=Path(args.out_spatial_png),
            out_grdc_vs_glofas_pdf=Path(args.out_grdc_vs_glofas_pdf),
            out_glofas_vs_atlite_png=Path(args.out_glofas_vs_atlite_png),
            grdc_station=args.grdc_station,
            glofas_dx=args.glofas_dx,
            grdc_dx=args.grdc_dx,
            k_scale=args.k_scale,
            ppl_bbox=dict(
                lat_min=args.lat_min,
                lat_max=args.lat_max,
                lon_min=args.lon_min,
                lon_max=args.lon_max,
            ),
            validation_ppl_idx=args.validation_ppl_idx,
        )
