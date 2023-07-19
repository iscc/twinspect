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
    """Plot pair-wise hamming distribution"""
    metrics_path = Path(metrics_path)
    log.debug(f"Plotting distribution for {metrics_path.name}")
    with metrics_path.open("r") as json_file:
        data = json.load(json_file)
    dist = data["metrics"].get("distribution", None)
    if dist is None:
        return

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
    """Plot effectiveness metrics"""
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
    ax.set_title(f"{title} | Precision, Recall, F1-Score", fontsize=18)

    df.plot(x="threshold", y="precision", ax=ax, label="Precision", marker="o", linestyle="-")
    df.plot(x="threshold", y="recall", ax=ax, label="Recall", marker="o", linestyle="-")
    df.plot(x="threshold", y="f1_score", ax=ax, label="F1 Score", marker="o", linestyle="-")

    plt.legend()
    plt.grid()

    x = df["threshold"].unique()  # Fix x-axis ticks to show only available threshold values
    if len(x) > 17:
        plt.xticks(np.arange(min(x), max(x) + 1, 2))
    else:
        plt.xticks(x)

    ax.set_xlabel("Hamming Distance Query Threshold", fontsize=16)
    ax.set_ylabel("Performance (higher is better)", fontsize=16)
    plt.tick_params(labelsize=12)
    plt.subplots_adjust(left=0.08, right=0.95, top=0.90, bottom=0.08)
    return plt


if __name__ == "__main__":
    fp = r"E:\twinspect\audio_code_v0_64-fma_5000-142e3bd331044320-metrics.json"
    # fp = r"E:\twinspect\audio_code_v0_256-fma_5000-142e3bd331044320-metrics.json"
    # print(get_title(fp))
    # plo = plot_distribution(fp)
    # plo.show()
    plo = plot_effectiveness(fp)
    plo.show()
