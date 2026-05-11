# SPDX-FileCopyrightText:  PyPSA-Earth and PyPSA-Eur Authors

# SPDX-License-Identifier: AGPL-3.0-or-later

# -*- coding: utf-8 -*-
"""
validate_system_metrics.py
==========================
Extracts and validates two system-level metrics from a solved PyPSA network:

1. Load shedding  — summed annually per bus. Reference is exactly zero
                    (any non-zero value is a model artefact to be minimised).

2. Imports & exports — annual cross-border flows (GWh) through links that
                       connect Zambia to neighbouring countries.
                       Reference values if not supplied, only model values are written.
"""

import logging
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import pypsa
from helpers import configure_logging, mock_snakemake

logger = logging.getLogger(__name__)


def extract_load_shedding(n: pypsa.Network) -> pd.DataFrame:
    """
    Return annual load shedding (GWh) per bus.
    The reference value for every bus is 0 GWh.
    """
    ls_gens = n.generators.query("carrier == 'load shedding'").index

    if ls_gens.empty:
        logger.info("No load-shedding generators found in network.")
        df = pd.DataFrame(columns=["bus", "load_shedding_gwh", "reference_gwh"])
        df["reference_gwh"] = 0.0
        return df

    ls_gen = (
        n.generators_t.p[ls_gens]
        .mul(n.snapshot_weightings.generators, axis=0)
        .sum()
    )
    ls_gen.index = n.generators.loc[ls_gens, "bus"]
    ls_gen.index.name = "bus"
    # clustering can place multiple load-shedding generators on the same bus;
    # groupby sums them so each bus is counted once
    ls_by_bus = ls_gen.groupby("bus").sum() / 1e3  # MW·h → GWh

    df = ls_by_bus.reset_index()
    df.columns = ["bus", "load_shedding_gwh"]
    df["reference_gwh"] = 0.0

    total = df["load_shedding_gwh"].sum()
    logger.info("Total load shedding: %.2f GWh across %d buses", total, len(df))
    if total > 0:
        logger.warning(
            "Non-zero load shedding detected (%.2f GWh). "
            "Consider increasing hydro inflow multiplier or adjusting capacity.",
            total,
        )

    return df


def plot_load_shedding(df: pd.DataFrame, output_path: Path) -> None:
    total = df["load_shedding_gwh"].sum()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(max(6, len(df) * 0.6 + 2), 4))

    if df.empty or total == 0:
        ax.text(0.5, 0.5, "No load shedding detected ✓",
                ha="center", va="center", fontsize=14, color="green",
                transform=ax.transAxes)
        ax.set_title("Annual Load Shedding by Bus")
    else:
        non_zero = df[df["load_shedding_gwh"] > 0]
        ax.bar(non_zero["bus"].astype(str), non_zero["load_shedding_gwh"],
               color="crimson", alpha=0.8)
        ax.set_xlabel("Bus ID")
        ax.set_ylabel("Load Shedding (GWh)")
        ax.set_title(f"Annual Load Shedding by Bus  (total: {total:.1f} GWh)")
        ax.yaxis.grid(True, linestyle="--", alpha=0.5)
        ax.set_axisbelow(True)
        plt.xticks(rotation=45, ha="right")

    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Saved load shedding plot → %s", output_path)

def extract_imports_exports(
    n: pypsa.Network,
    country: str = "ZM",
) -> dict:
    """
    Compute annual cross-border imports and exports (GWh) for `country`.
    """
    flows_gwh = (
        n.links_t.p0
        .mul(n.snapshot_weightings.objective, axis=0)
        .sum() / 1e3
    )

    imports_total = 0.0
    exports_total = 0.0
    rows = []

    # Assumptions:
    # - PyPSA-Earth tags every bus with an ISO2 'country' attribute.
    # - Cross-border links are two-bus (bus0/bus1 only); multi-port buses
    #   (bus2…bus4) are not used for cross-border flows.
    # - PyPSA sign convention: p0 > 0 means power flows bus0 → bus1.
    #   When the target country is on bus0, positive p0 is an export.
    #   When it is on bus1, positive p0 is an import (signs reversed).
    for link in n.links.index:
        bus0 = n.links.loc[link, "bus0"]
        bus1 = n.links.loc[link, "bus1"]
        c0 = n.buses.loc[bus0, "country"]
        c1 = n.buses.loc[bus1, "country"]

        if c0 == country:
            flow = flows_gwh[link]
            # flow is a signed annual net: clip to zero to split into
            # non-negative export and import components
            exp = max(flow, 0.0)
            imp = max(-flow, 0.0)
        elif c1 == country:
            flow = flows_gwh[link]
            imp = max(flow, 0.0)
            exp = max(-flow, 0.0)
        else:
            continue

        exports_total += exp
        imports_total += imp
        rows.append({
            "link": link,
            "bus0": bus0,
            "bus1": bus1,
            "country_bus0": c0,
            "country_bus1": c1,
            "exports_gwh": round(exp, 2),
            "imports_gwh": round(imp, 2),
        })

    flows_df = pd.DataFrame(rows)
    net = exports_total - imports_total

    logger.info(
        "Imports: %.1f GWh  |  Exports: %.1f GWh  |  Net exports: %.1f GWh",
        imports_total, exports_total, net,
    )

    return {
        "imports_gwh": round(imports_total, 2),
        "exports_gwh": round(exports_total, 2),
        "net_exports_gwh": round(net, 2),
        "flows_by_link": flows_df,
    }


def plot_imports_exports(
    result: dict,
    reference_imports: float | None,
    reference_exports: float | None,
    output_path: Path,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    labels = ["Imports", "Exports"]
    model_vals = [result["imports_gwh"], result["exports_gwh"]]

    fig, ax = plt.subplots(figsize=(6, 4))
    x = range(len(labels))
    width = 0.35

    ax.bar([i - width / 2 for i in x], model_vals, width,
           label="PyPSA-Earth model", color="coral")

    if reference_imports is not None and reference_exports is not None:
        ref_vals = [reference_imports, reference_exports]
        ax.bar([i + width / 2 for i in x], ref_vals, width,
               label="Reference", color="steelblue")

    ax.set_xticks(list(x))
    ax.set_xticklabels(labels)
    ax.set_ylabel("Energy (GWh)")
    ax.set_title("Annual Zambia Cross-Border Flows")
    ax.legend()
    ax.yaxis.grid(True, linestyle="--", alpha=0.5)
    ax.set_axisbelow(True)

    # Net exports annotation
    net = result["net_exports_gwh"]
    ax.annotate(
        f"Net exports: {net:+.1f} GWh",
        xy=(0.5, 0.95), xycoords="axes fraction",
        ha="center", va="top", fontsize=9,
        bbox=dict(boxstyle="round,pad=0.3", fc="lightyellow", ec="gray"),
    )

    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Saved imports/exports plot → %s", output_path)


def main(snakemake) -> None:
    network_path            = Path(snakemake.input.network)
    out_load_shedding_csv   = Path(snakemake.output.load_shedding_csv)
    out_load_shedding_png   = Path(snakemake.output.load_shedding_png)
    out_imports_exports_csv = Path(snakemake.output.imports_exports_csv)
    out_imports_exports_png = Path(snakemake.output.imports_exports_png)
    country                 = snakemake.params.country
    reference_imports_gwh   = snakemake.params.get("reference_imports_gwh", None)
    reference_exports_gwh   = snakemake.params.get("reference_exports_gwh", None)

    logger.info("Loading network from %s", network_path)
    n = pypsa.Network(str(network_path))

    ls_df = extract_load_shedding(n)

    out_load_shedding_csv.parent.mkdir(parents=True, exist_ok=True)
    ls_df.to_csv(out_load_shedding_csv, index=False)
    logger.info("Saved load shedding CSV → %s", out_load_shedding_csv)

    plot_load_shedding(ls_df, out_load_shedding_png)

    ie_result = extract_imports_exports(n, country=country)

    # Summary row
    summary = pd.DataFrame([{
        "imports_gwh": ie_result["imports_gwh"],
        "exports_gwh": ie_result["exports_gwh"],
        "net_exports_gwh": ie_result["net_exports_gwh"],
        "reference_imports_gwh": reference_imports_gwh,
        "reference_exports_gwh": reference_exports_gwh,
    }])

    # Detailed per-link breakdown
    ie_full = pd.concat(
        [summary, ie_result["flows_by_link"]],
        axis=0, ignore_index=True,
    )

    out_imports_exports_csv.parent.mkdir(parents=True, exist_ok=True)
    ie_full.to_csv(out_imports_exports_csv, index=False)
    logger.info("Saved imports/exports CSV → %s", out_imports_exports_csv)

    plot_imports_exports(
        ie_result, reference_imports_gwh, reference_exports_gwh,
        out_imports_exports_png,
    )


if __name__ == "__main__":
    if "snakemake" not in globals():
        snakemake = mock_snakemake("validate_system_metrics")
    configure_logging(snakemake)
    main(snakemake)
