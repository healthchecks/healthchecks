# GitHub Actions

You can augment your GitHub Actions workflows to report success and
failure to SITE_NAME:

```yaml
name: Hourly Housekeeping
on:
  schedule:
    - cron: '15 * * * *'
jobs:
  Main-Job:
    runs-on: ubuntu-latest
    steps:
      - run: echo "Running housekeeping tasks..."
  Ping-Success:
    runs-on: ubuntu-latest
    needs: [Main-Job]
    steps:
      - run: curl -m 10 --retry 5 ${{ secrets.ping_url }}
  Ping-Failure:
    runs-on: ubuntu-latest
    if: ${{ failure() }}
    needs: [Main-Job]
    steps:
      - run: curl -m 10 --retry 5 ${{ secrets.ping_url }}/fail
```

Note how the jobs `Ping-Success` and `Ping-Failure` define `Main-Job` as
their dependency. `Ping-Success` runs only if `Main-Job` completes
successfully, and `Ping-Failure` runs when `Main-Job` fails.

To avoid exposing the ping URL, it is a good idea to define it
as [a secret](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
and access it via the `secrets` context.

## Using the `workflow_run` Trigger

Alternatively, you can put the pinging logic in a separate workflow,
and configure it to trigger every time your main workflow finishes. The main workflow:

```yaml
name: Hourly Housekeeping
on:
  schedule:
    - cron: '15 * * * *'
jobs:
  Main-Job:
    runs-on: ubuntu-latest
    steps:
      - run: echo "Running housekeeping tasks..."
```

And the monitoring workflow:

```yaml
name: Ping SITE_NAME
on:
  workflow_run:
    workflows: ['Hourly Housekeeping']
    types: [completed]
jobs:
  Ping-Success:
    runs-on: ubuntu-latest
    if: ${{ github.event.workflow_run.conclusion == 'success' }}
    steps:
      - run: curl -m 10 --retry 5 ${{ secrets.ping_url }}
  Ping-Failure:
    runs-on: ubuntu-latest
    if: ${{ github.event.workflow_run.conclusion == 'failure' }}
    steps:
      - run: curl -m 10 --retry 5 ${{ secrets.ping_url }}/fail
```