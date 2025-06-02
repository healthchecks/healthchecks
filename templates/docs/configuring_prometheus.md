# Configuring Prometheus

SITE_NAME supports exporting metrics and check statuses to
[Prometheus](https://prometheus.io/), for use with [Grafana](https://grafana.com/).

## Create read-only API key

Create a read-only API key in <strong>Project Settings › API Access</strong>.

Make sure to use a <strong>read-only</strong> API key. Prometheus does not need
read-write API access.

![Project's API Keys](IMG_URL/prometheus_api_keys.png)

## Update the prometheus.yml

Add the following scrape configuration to Prometheus:

```yaml
  - job_name: "healthchecks"
    scrape_interval: 60s
    scheme: SITE_SCHEME
    metrics_path: /projects/{your-project-uuid}/metrics/{your-readonly-api-key}
    static_configs:
      - targets: ["SITE_HOSTNAME"]
```

The "{your-project-uuid}" is the UUID you see in your browser's address bar
when viewing a list of checks for a particular project.

Reload Prometheus, and your changes should be live, coming in under the `hc_` prefix.

## Available Metrics

The Prometheus metrics endpoint exports the following metrics:

hc_check_up
:   For every check, indicates whether the check is currently up
    (1 for yes, 0 for no).

    Labels:

    * `name` – the name of the check
    * `tags` – check's tags as a text string; multiple tags are delimited with spaces
    * `unique_key` – a stable, unique identifier of the check (derived from the check's code)

hc_check_started
:   For every check, indicates whether the check is currently running
    (1 for yes, 0 for no).

    Labels:

    * `name` – the name of the check
    * `tags` – check's tags as a text string; multiple tags are delimited with spaces
    * `unique_key` – a stable, unique identifier of the check (derived from the check's code)

hc_tag_up
:   For every tag, indicates whether all checks with this tag are up
    (1 for yes, 0 for no).

    Labels:

    * `tag` – name of the tag

hc_checks_total
:   The total number of checks.

hc_checks_down_total
:   <br>The number of checks currently down.

## Constructing URLs to Check Details Pages

You can use the `unique_key` labels to construct URLs to check's
details pages in SITE_NAME. Construct the URLs like so:

```
SITE_ROOT/cloaked/{unique_key}/
```

## Working With Grafana Cloud

Grafana Cloud requires the metrics endpoints to be authenticated using either
HTTP "Basic" or "Bearer" authentication scheme. It refuses to scrape public endpoints.
To fulfil this requirement, SITE_NAME provides an alternate metrics endpoint which
requires "Bearer" authentication. Use the following settings with Grafana Cloud:

* Scrape Job URL: `SITE_ROOT/projects/{your-project-uuid}/metrics/`
* Authentication type: Bearer
* Bearer token: the read-only API key
