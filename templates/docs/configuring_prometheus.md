# Configuring Prometheus

SITE_NAME supports exporting metrics and check statuses to
[Prometheus](https://prometheus.io/), for use with [Grafana](https://grafana.com/).

You can generate the metrics export endpoint by going to your project settings
and **creating a read-only API key**. You will then see the link to
the Prometheus endpoint:

![Project's API Keys](IMG_URL/prometheus_endpoint.png)

## Update the prometheus.yml

You can copy the Prometheus endpoint URL and add it to the Prometheus configuration:

```yaml
  - job_name: "healthchecks"
    scrape_interval: 60s
    scheme: SITE_SCHEME
    metrics_path: /projects/45sd78-eeee-dddd-8888-b25a9887ecfd/metrics/NXyGzks4s8xcF1J-wzoaioyoqXIANGD0
    static_configs:
      - targets: ["SITE_HOSTNAME"]
```

Notice how we split up the URL and paste in the scheme, domain, and path separately.

Reload Prometheus, and your changes should be live, coming in under the `hc_` prefix.
