import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import base64
from io import BytesIO
from jinja2 import Template
from twinspect import CODE_DIR


def load_results(filenames):
    results = []
    for filename in filenames:
        with open(filename, "r") as file:
            results.append(json.load(file))
    return results


def create_dataframe(results):
    rows = []
    for result in results:
        for metric in result["metrics"]["effectiveness"]:
            row = {
                "algorithm": result["algorithm"],
                "dataset": result["dataset"],
                "threshold": metric["threshold"],
                "precision": metric["precision"],
                "recall": metric["recall"],
                "f1_score": metric["f1_score"],
                "accuracy": metric["accuracy"],
                "jaccard_index": metric["jaccard_index"],
                "mcc": metric["mcc"],
                "speed": result["metrics"]["speed"]["mean_human"],
            }
            rows.append(row)
    return pd.DataFrame(rows)


def plot_graph(df, title):
    fig, ax = plt.subplots()
    df.plot(x="threshold", y="precision", ax=ax, label="Precision", marker="o", linestyle="-")
    df.plot(x="threshold", y="recall", ax=ax, label="Recall", marker="o", linestyle="-")
    df.plot(x="threshold", y="f1_score", ax=ax, label="F1 Score", marker="o", linestyle="-")

    plt.title(title)
    plt.legend()
    plt.grid()

    x = df["threshold"].unique()  # Fix x-axis ticks to show only available threshold values
    if len(x) > 17:
        plt.xticks(np.arange(min(x), max(x) + 1, 2))
    else:
        plt.xticks(x)
    plt.tick_params(axis="x", labelsize=7)
    buf = BytesIO()
    plt.savefig(buf, format="png", dpi=150)
    buf.seek(0)
    img_data = buf.getvalue()
    buf.close()

    return base64.b64encode(img_data).decode()


def render_markdown(df, plot_data):
    template_str = """
# TwinSpect Benchmark Results

## Overview

| Algorithm | Dataset | Threshold | Precision | Recall | F1 Score | Speed |
| --------- | ------- | --------- | --------- | ------ | -------- | ----- |
{% for row in rows -%}
| {{ row['algorithm'] }} | {{ row['dataset'] }} | {{ row['threshold'] }} | {{ row['precision']|round(2) }} | {{ row['recall']|round(2) }} | {{ row['f1_score']|round(2) }} | {{ row['speed'] }} |
{% endfor %}

## Algorithm/Dataset Plots

{% for plot_key, plot_value in plot_data.items() %}
### {{ plot_key }}

![{{ plot_key }}]({{ plot_value }})

{% endfor %}
"""

    template = Template(template_str)

    md = template.render(
        rows=df.to_dict(orient="records"),
        plot_data=plot_data,
    )

    result_path = CODE_DIR / "docs/results.md"

    with open(result_path, "w") as file:
        file.write(md)


def generate_report(filenames):
    results = load_results(filenames)
    df = create_dataframe(results)

    unique_thresholds = sorted(df["threshold"].unique())
    # ideal_threshold_idx = len(unique_thresholds) // 8
    ideal_threshold_idx = 4
    ideal_threshold = unique_thresholds[ideal_threshold_idx]

    overview_df = df[df["threshold"] == ideal_threshold]  # DataFrame for the main table (overview)

    # overview_df = df[df["threshold"] == 8]  # DataFrame for the main table (overview)
    plot_data = {}
    for _, row in overview_df.iterrows():
        plot_key = f"{row['algorithm']} - {row['dataset']}"
        subset_df = df[(df["algorithm"] == row["algorithm"]) & (df["dataset"] == row["dataset"])]
        plot_data[plot_key] = "data:image/png;base64," + plot_graph(subset_df, plot_key)

    render_markdown(overview_df, plot_data)


if __name__ == "__main__":
    filenames = [
        r"E:\twinspect\audio_code_v0_64-fma_5000-142e3bd331044320-metrics.json",
        r"E:\twinspect\audio_code_v0_256-fma_5000-142e3bd331044320-metrics.json",
        r"E:\twinspect\image_code_v0_64-pin_5000-b3b1e6f121e3fb48-metrics.json",
        r"E:\twinspect\image_code_v0_256-pin_5000-b3b1e6f121e3fb48-metrics.json",
    ]
    generate_report(filenames)
