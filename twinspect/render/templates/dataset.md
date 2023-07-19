---

### {{ data.dataset_label }}

!!! abstract inline end "Dataset Info"
    - **ID**: {{ data.checksum }}
    - **Mode**: {{ data.dataset_mode | title }}
    - **Size**: {{ data.total_size }}
    - **Files**: {{ data.total_files }}

The **{{ data.dataset_label }}** is a benchmark dataset, designed to assess the accuracy of
{{ data.dataset_mode }} identification algorithms. It includes ground truth data for a total of
**{{ data.total_files }} {{ data.dataset_mode }} files** with near-duplicates organized into
**{{ data.total_clusters }} clusters**.

{% if data.total_distractor_files %}Additionally, the dataset contains
**{{ data.total_distractor_files }} unique** {{ data.dataset_mode }} files, with no corresponding
duplicates within the set.
{% endif %}

{% if data.dataset_info %}
{{ data.dataset_info }}
{% endif %}

??? note "Clustering Details"
    {% if data.cluster_sizes.min !=  data.cluster_sizes.max %}
    Clusters contain an average of **{{ data.cluster_sizes.mean | round(precision=2) }}
    near-duplicate** {{ data.dataset_mode }} files.{% else %}Each cluster contains
    **{{ data.cluster_sizes.max}} near-duplicate** {{ data.dataset_mode }} files.
    {% endif %}

    {% if data.cluster_sizes.min !=  data.cluster_sizes.max %}
    **Cluster sizes**

    - **Minimum**: {{ data.cluster_sizes.min }}
    - **Maximum**: {{ data.cluster_sizes.max }}
    - **Mean**: {{ data.cluster_sizes.mean | round(precision=2) }}
    - **Median**: {{ data.cluster_sizes.median | round(precision=2) }}
    {% endif %}

{% if data.transformations %}
??? note "Synthetic Transformations"
    The following transformations were applied to **{{ data.total_clusters }} files** of the
    dataset to simulate different conditions that might be encountered in real-world applications:
{% for transform  in data.transformations %}
    - {{ transform  -}}
{% endfor %}
{% endif %}


