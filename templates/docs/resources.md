# Third-Party Resources

A collection of third-party software projects that integrate with SITE_NAME.
Please submit additions and corrections
[on GitHub](https://github.com/healthchecks/healthchecks/issues).

## Tools for Self-Hosting

* [linuxserver/docker-healthchecks](https://github.com/linuxserver/docker-healthchecks) – Alternative Docker image
* [galexrt/docker-healthchecks](https://github.com/galexrt/docker-healthchecks) – Alternative Docker image
* [ansible-collections/community.healthchecksio](https://github.com/ansible-collections/community.healthchecksio) - Ansible modules for automating tasks on Healthchecks.io

## Command Runners, Shell Wrappers

* [runitor](https://github.com/bdd/runitor) - A command runner with Healthchecks.io integration to keep your scripts and containers simple.
* [crontask.sh](https://github.com/pforret/crontask) – Bash wrapper to use in crontab. Supports pinging.
* [task-mon](https://github.com/dimo414/task-mon) – A small binary for notifying Healthchecks.io when a command runs, written in Rust.
* [hc-monitor](https://gist.github.com/odolbeau/bd6d8eb7910d1289e2687682c8db9275) – Bash wrapper, supports pinging.

## API Wrappers

### Go

* [kristofferahl/go-healthchecksio](https://github.com/kristofferahl/go-healthchecksio) – Supports listing, creating, updating, deleting, pausing, pinging.

### PowerShell

* [davehope/HealthChecksIOStatusReport](https://github.com/davehope/HealthChecksIOStatusReport) – Supports pinging.

### Python

* [samarpan-rai/healthchecks_wrapper](https://github.com/samarpan-rai/healthchecks_wrapper) – Python context manager, supports pinging.
* [danidelvalle/healthchecks-decorator](https://github.com/danidelvalle/healthchecks-decorator) – Python context manager, supports pinging.

### Rust

* [msfjarvis/healthchecks-rs](https://github.com/msfjarvis/healthchecks-rs) – Supports all current Ping API and Management API calls.

### Terraform

* [terraform-provider-healthchecksio](https://github.com/kristofferahl/terraform-provider-healthchecksio) – Terraform Provider for Healthchecks.io. Supports creating, updating, deleting checks.

## Backup Software Integrations

* [binarybucks/restic-tools](https://github.com/binarybucks/restic-tools) – Wrapper around restic backup, with Healthchecks.io support.
* [borgmatic](https://torsion.org/borgmatic/docs/how-to/monitor-your-backups/#healthchecks-hook) – A frontend to Borg, includes Healthchecks.io support.
* [emborg](https://emborg.readthedocs.io/en/latest/monitoring.html#healthchecks-io) – A frontend to Borg, includes Healthchecks.io support.

## Dashboards

* [healthchecks/dashboard](https://github.com/healthchecks/dashboard) – A standalone HTML page showing the status of the checks in your account.
* [nicoandrade/healthchecks-front](https://github.com/nicoandrade/healthchecks-front) – Beautiful & free web dashboard, works great on desktop and mobile.
