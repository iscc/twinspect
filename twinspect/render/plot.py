"""Create plots from metrics"""

import matplotlib.pyplot as plt
from pathlib import Path
import json
import numpy as np
import pandas as pd
from loguru import logger as log


def get_data(metrics_path):
    metrics_path = Path(metrics_path)
    with metrics_path.open("r") as json_file:
        data = json.load(json_file)
    return data


def get_title(metrics_path):
    """Construct plot title"""
    data = get_data(metrics_path)
    algo_name = " ".join(data["algorithm"].split("_")).title()
    ds_name = " ".join(data["dataset"].split("_")).title()
    return f"{algo_name} | Dataset {ds_name}"


def big_num(num):
    for unit in ["", "K", "M", "B", "T"]:
        if abs(num) < 1000:
            return f"{num:.1f}{unit}"
        num /= 1000
    return f"{num:.1f}P"


def plot_distribution(metrics_path):
    """Plot intra-cluster and inter-cluster hamming distance distributions."""
    metrics_path = Path(metrics_path)
    log.debug(f"Plotting distribution for {metrics_path.name}")
    with metrics_path.open("r") as json_file:
        data = json.load(json_file)
    dist = data["metrics"].get("distribution", None)
    if dist is None:
        return

    # Handle both old format (single dict) and new format (with intra/inter)
    if "intra" in dist and "inter" in dist:
        return plot_distribution_separated(metrics_path, dist)
    else:
        return plot_distribution_legacy(metrics_path, dist)


def plot_distribution_separated(metrics_path, dist):
    """Plot separate intra-cluster and inter-cluster distributions."""
    intra = {int(k): v for k, v in dist["intra"].items()}
    inter = {int(k): v for k, v in dist["inter"].items()}

    # Determine max distance for x-axis
    all_keys = set(intra.keys()) | set(inter.keys())
    if not all_keys:
        return
    max_dist = max(all_keys)

    # Create aligned arrays for plotting
    x_range = np.arange(max_dist + 1)
    intra_values = np.array([intra.get(x, 0) for x in x_range], dtype=float)
    inter_values = np.array([inter.get(x, 0) for x in x_range], dtype=float)

    # Create figure
    fig, ax = plt.subplots(figsize=(13, 9))

    # Bar width and positioning
    bar_width = 0.4
    x_intra = x_range - bar_width / 2
    x_inter = x_range + bar_width / 2

    # Plot both distributions side by side
    # Use log scale but handle zeros by setting minimum to 0.5 for visibility
    intra_plot = np.where(intra_values > 0, intra_values, 0.5)
    inter_plot = np.where(inter_values > 0, inter_values, 0.5)

    ax.bar(
        x_intra,
        intra_plot,
        width=bar_width,
        label="Intra-cluster (positives)",
        color="#2ecc71",
        alpha=0.8,
    )
    ax.bar(
        x_inter,
        inter_plot,
        width=bar_width,
        label="Inter-cluster (negatives)",
        color="#3498db",
        alpha=0.8,
    )

    ax.set_yscale("log")

    # Configure x-axis ticks
    if max_dist <= 64:
        plt.xticks(list(range(0, max_dist + 1, 2 if max_dist <= 32 else 4)))
    else:
        plt.xticks(list(range(0, max_dist + 1, 8)))

    plt.tick_params(labelsize=12)
    plt.subplots_adjust(left=0.08, right=0.95, top=0.88, bottom=0.10)

    # Labels and title
    title = get_title(metrics_path)
    total_intra = sum(intra.values())
    total_inter = sum(inter.values())
    fig.suptitle("Distance Distribution: Positives vs Negatives", fontsize=20, fontweight="bold")
    ax.set_title(
        f"{title} | {big_num(total_intra)} positive pairs, {big_num(total_inter)} negative pairs",
        fontsize=16,
    )
    ax.set_xlabel("Hamming Distance", fontsize=16)
    ax.set_ylabel("Frequency (log scale)", fontsize=16)
    ax.legend(loc="upper right", fontsize=14)

    # Add vertical line at crossover point (if any)
    crossover = find_crossover(intra, inter)
    if crossover is not None:
        ax.axvline(
            x=crossover,
            color="#e74c3c",
            linestyle="--",
            linewidth=2,
            label=f"Crossover ≈ {crossover}",
        )
        ax.legend(loc="upper right", fontsize=14)

    return plt


def find_crossover(intra, inter):
    """Find approximate crossover point where inter-cluster frequency exceeds intra-cluster."""
    if not intra or not inter:
        return None
    max_dist = max(max(intra.keys(), default=0), max(inter.keys(), default=0))
    for d in range(max_dist + 1):
        intra_freq = intra.get(d, 0)
        inter_freq = inter.get(d, 0)
        if inter_freq > intra_freq and intra_freq > 0:
            return d
    return None


def plot_distribution_legacy(metrics_path, dist):
    """Plot legacy single distribution format for backward compatibility."""
    dist = {int(k): v for k, v in dist.items()}
    keys = list(dist.keys())
    values = list(dist.values())

    # create a figure and axis
    fig, ax = plt.subplots(figsize=(13, 9))

    # create histogram
    if len(dist) <= 64:
        ax.bar(keys, values, log=True)
        plt.xticks(list(range(0, 65, 2)))
    else:
        # create bins of size 4 if there are more than 64 distances
        bins = np.arange(min(keys), max(keys) + 4, 4)
        hist, bin_edges = np.histogram(keys, bins=bins, weights=values)
        # reduce the width of the bars a bit to add whitespace between them
        ax.bar(bin_edges[:-1], hist, width=3.2, align="edge", log=True)
        plt.xticks(bin_edges[::2])  # adjust x-ticks to match bin size

    plt.tick_params(labelsize=12)
    plt.subplots_adjust(left=0.08, right=0.95, top=0.92, bottom=0.08)

    # set labels
    title = get_title(metrics_path)
    total = sum(dist.values())
    fig.suptitle("Pair-Wise Distance Distribution", fontsize=20, fontweight="bold")
    ax.set_title(f"{title} | {big_num(total)} pairs", fontsize=18)
    ax.set_xlabel("Hamming Distance", fontsize=16)
    ax.set_ylabel("Frequency (log scale)", fontsize=16)
    return plt


def plot_effectiveness(metrics_path):
    """Plot effectiveness metrics with optional standard deviation bands."""
    metrics_path = Path(metrics_path)
    log.debug(f"Plotting effectiveness for {metrics_path.name}")
    with metrics_path.open("r") as json_file:
        data = json.load(json_file)
    eff = data["metrics"].get("effectiveness", None)
    if eff is None:
        return
    df = pd.DataFrame(eff)
    fig, ax = plt.subplots(figsize=(13, 9))
    fig.suptitle("Matching Effectiveness", fontsize=20, fontweight="bold")
    title = get_title(metrics_path)

    # Check if standard deviation data is available
    has_std = "precision_std" in df.columns and "recall_std" in df.columns

    if has_std:
        # Use recall query count as the primary indicator (cluster members only)
        num_queries = (
            df["num_queries_recall"].iloc[0] if "num_queries_recall" in df.columns else "N/A"
        )
        ax.set_title(f"{title} | Precision, Recall, F1-Score (n={num_queries} files)", fontsize=18)
    else:
        ax.set_title(f"{title} | Precision, Recall, F1-Score", fontsize=18)

    x = df["threshold"].values
    colors = {"precision": "#1f77b4", "recall": "#ff7f0e", "f1_score": "#2ca02c"}

    # Plot precision with optional std band
    ax.plot(
        x, df["precision"], label="Precision", marker="o", linestyle="-", color=colors["precision"]
    )
    if has_std:
        ax.fill_between(
            x,
            np.clip(df["precision"] - df["precision_std"], 0, 1),
            np.clip(df["precision"] + df["precision_std"], 0, 1),
            alpha=0.2,
            color=colors["precision"],
        )

    # Plot recall with optional std band
    ax.plot(x, df["recall"], label="Recall", marker="o", linestyle="-", color=colors["recall"])
    if has_std:
        ax.fill_between(
            x,
            np.clip(df["recall"] - df["recall_std"], 0, 1),
            np.clip(df["recall"] + df["recall_std"], 0, 1),
            alpha=0.2,
            color=colors["recall"],
        )

    # Plot F1 score (no std band as it's derived from precision and recall)
    ax.plot(
        x, df["f1_score"], label="F1 Score", marker="o", linestyle="-", color=colors["f1_score"]
    )

    plt.legend()
    plt.grid()

    # Fix x-axis ticks to show only available threshold values
    if len(x) > 17:
        plt.xticks(np.arange(min(x), max(x) + 1, 2))
    else:
        plt.xticks(x)

    ax.set_xlabel("Hamming Distance Query Threshold", fontsize=16)
    ax.set_ylabel("Performance (higher is better)", fontsize=16)
    ax.set_ylim(0, 1.05)  # Metrics are bounded 0-1
    plt.tick_params(labelsize=12)
    plt.subplots_adjust(left=0.08, right=0.95, top=0.90, bottom=0.08)
    return plt
