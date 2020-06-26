# Configuring Prometheus

Healthchecks.io supports exporting metrics and check statuses to [Prometheus](https://prometheus.io/), for use with [Grafana](https://grafana.com/).  

You can generate the metrics export endpoint by going to your project settings (last tab up top) and clicking "Create API Keys". You will then see the link to the prometheus endpoint, which looks like this:

```
https://healthchecks.io/projects/45sd78-eeee-dddd-8888-b25a9887ecfd/metrics/NXyGzks4s8xcF1J-wzoaioyoqXIANGD0
```

## Update the prometheus.yml

You can take that link and add it to the prometheus config:

```yaml
  - job_name: "healthchecks"
    scrape_interval: 60s
    scheme: https
    metrics_path: /projects/45sd78-eeee-dddd-8888-b25a9887ecfd/metrics/NXyGzks4s8xcF1J-wzoaioyoqXIANGD0
    static_configs:
      - targets: ["healthchecks.io"]
```

Notice how we split up the URL and paste in the scheme, domain, and path separately. 

Reload promethus and your changes should be live, coming in under the `hc_` prefix.
