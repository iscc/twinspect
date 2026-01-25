# {{ data.title }} Results

!!! info
    Benchmark results for {{ data.title | lower }} similarity algorithms.

## Overview

| Algorithm | Dataset | Threshold | Recall | Precision | F1-Score |
| --------- | ------- | --------- | ------ | --------- | -------- |
{% for row in data.overview -%}
| {{ row.algorithm }} | {{ row.dataset }} | {{ row.threshold }} | {{ row.recall | round(2) }} | {{ row.precision | round(2) }} | {{ row.f1_score | round(2) }} |
{% endfor %}

{% if data.explanation %}
{{ data.explanation }}
{% endif %}

