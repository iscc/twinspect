import json
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
            }
            rows.append(row)
    return pd.DataFrame(rows)


def plot_graph(df, column, title):
    fig, ax = plt.subplots()
    for name, group in df.groupby("algorithm"):
        group.plot(x="threshold", y=column, ax=ax, label=name, marker="o", linestyle="-")

    plt.title(title)
    plt.legend()
    plt.grid()

    buf = BytesIO()
    plt.savefig(buf, format="png", dpi=150)
    buf.seek(0)
    img_data = buf.getvalue()
    buf.close()

    return base64.b64encode(img_data).decode()


def render_markdown(df, plot_data):
    template_str = """
# TwinSpect Benchmark Results

{% for dataset in datasets %}
## Dataset: {{ dataset }}

### Performance Metrics

| Algorithm | Threshold | Precision | Recall | F1 Score |
| --------- | --------- | --------- | ------ | -------- |
{% for row in rows -%}
{% if row.dataset == dataset -%}
| {{ row.algorithm }} | {{ row.threshold }} | {{ row.precision }} | {{ row.recall }} | {{ row.f1_score }} |
{% endif %}
{%- endfor %}

### Plots

![Precision vs Threshold]({{ plot_data[dataset]['precision'] }})

![Recall vs Threshold]({{ plot_data[dataset]['recall'] }})

![F1 Score vs Threshold]({{ plot_data[dataset]['f1_score'] }})

{%- endfor %}
"""

    template = Template(template_str)
    datasets = df["dataset"].unique().tolist()

    md = template.render(
        datasets=datasets,
        rows=df.itertuples(),
        plot_data=plot_data,
    )

    result_path = CODE_DIR / "docs/results.md"

    with open(result_path, "w") as file:
        file.write(md)


def generate_report(filenames):
    results = load_results(filenames)
    df = create_dataframe(results)

    plot_data = {}
    for dataset in df["dataset"].unique():
        dataset_df = df[df["dataset"] == dataset]
        plot_data[dataset] = {
            "precision": "data:image/png;base64,"
            + plot_graph(dataset_df, "precision", "Precision vs Threshold"),
            "recall": "data:image/png;base64,"
            + plot_graph(dataset_df, "recall", "Recall vs Threshold"),
            "f1_score": "data:image/png;base64,"
            + plot_graph(dataset_df, "f1_score", "F1 Score vs Threshold"),
        }

    render_markdown(df, plot_data)


if __name__ == "__main__":
    filenames = [
        r"E:\twinspect\audio_code_v0_64-fma_10-345f559585b38b7c-metrics.json",
        r"E:\twinspect\audio_code_v0_64-fma_100-6a10989f77611d16-metrics.json",
        r"E:\twinspect\image_code_v0_64-pin_100-9294a59d89021d37-metrics.json",
        r"E:\twinspect\image_code_v0_64-pin_1000-d05a8953f724c958-metrics.json",
        r"E:\twinspect\audio_code_v0_256-fma_100-6a10989f77611d16-metrics.json",
        r"E:\twinspect\image_code_v0_256-pin_1000-f9ba7fb300ead3bf-metrics.json"
        # Add more result files as needed.
    ]
    generate_report(filenames)
