---

## {{ data.name }}

{{ data.info }}

{% if data.url %}
The reference implementation is available in the
[`{{ data.url | replace("https://github.com/", "") | replace("/blob/main/", " - ") }}`]({{ data.url }}) GitHub
Repository
{% endif %}

