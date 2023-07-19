---

## {{ data.algorithm }}

Evaluation against dataset **{{ data.dataset }}**

{% if data.plot_eff %}
### Effectiveness

??? question "Understanding the Effectiveness Chart"
    This chart evaluates the effectiveness of a similarity hash in comparing media files. Each hash
    is compared against all others at different distance thresholds, with results assessed against
    the ground truth.

    **Chart Interpretation**:

    - The **X-Axis** shows "Hamming Distance Query Thresholds". Each threshold marks a maximum distance
      for two hashes to be considered similar.
    - The **Y-Axis** represents Recall, Precision, and F1-Score:
    - **Recall**: The fraction of actual matches correctly identified by the hash. Higher recall
      indicates better match detection.
    - **Precision**: The ratio of correct predictions to the total number of predictions. Higher
      precision implies more reliable predictions.
    - **F1-Score**: Harmonic mean of Precision and Recall, balancing both measures. A high F1-score
      signals an effective algorithm.

    The curves display how these metrics vary across thresholds.

![{{ data.algorithm }} / {{ data.dataset }} / Effectiveness]({{ data.plot_eff }})

{% endif %}

{% if data.metrics.robustness %}
### Robustness

| Transformation | Minimum | Maximum | Mean | Median |
| -------------- | ------- | ------- | ---- | ------ |
{% for row in data.metrics.robustness  -%}
| {{ row.transform }} | {{ row.min }} | {{ row.max }} | {{ row.mean }} | {{ row.median }} |
{% endfor %}
{% endif %}

{% if data.plot_dist %}
### Distribution

![{{ data.algorithm }} / {{ data.dataset }} / Distribution]({{ data.plot_dist }})
{% endif %}

{% if data.metrics.speed %}
### Performance

!!! danger ""
    - **Minimum**: {{ data.metrics.speed.min_human }}
    - **Maximum**: {{ data.metrics.speed.max_human }}
    - **Mean**: {{ data.metrics.speed.mean_human }}
    - **Median**: {{ data.metrics.speed.median_human }}
{% endif %}


