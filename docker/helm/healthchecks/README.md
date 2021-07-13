

# Running with Helm

This is a sample configuration for running Healthchecks with kubernetes and helm

**Note: The Helm configuration is a recent addition, and, for the time being,
should be considered as highly experimental**.

Note: For the sake of simplicity, the sample configuration starts a single database
pod and a single web server pod, both on the same namespace. 

## Getting Started

* Add your configuration in the `/docker/helm/healthchecks/values.yaml` file.
  As a minimum, set the following fields:
    * `env.DEFAULT_FROM_EMAIL` – the "From:" address for outbound emails
    * `env.EMAIL_HOST` – the SMTP server
    * `env.EMAIL_HOST_PASSWORD` – the SMTP password
    * `env.EMAIL_HOST_USER` – the SMTP username
    * `postgresql.postgresqlPassword` – set to a random value
    * 'ingress.host: healthchecks.example.com'
* Deploy to k8s with helm:

        ```
        helm repo add bitnami https://charts.bitnami.com/bitnami
        helm repo update
        helm dependency update docker/helm/healthchecks
        helm install healthchecks  docker/helm/healthchecks --create-namespace -n healthchecks
        ```

* Open https://healthchecks.example.com in your browser and log in with
  the credentials from the previous step.

