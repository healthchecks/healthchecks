# SITE_NAME Documentation

SITE_NAME is a service for monitoring cron jobs and similar periodic processes:

* SITE_NAME **listens for HTTP requests ("pings")** from services being monitored.
* It **keeps silent** as long as pings arrive on time.
* It **raises an alert** as soon as a ping does not arrive on time.

SITE_NAME works as a [dead man's switch](https://en.wikipedia.org/wiki/Dead_man%27s_switch) for processes that need to
run continuously or on regular, known schedule. For example:

* filesystem backups, database backups
* task queues
* database replication status
* report generation scripts
* periodic data import and sync jobs
* periodic antivirus scans
* DDNS updater scripts
* SSL renewal scripts

SITE_NAME is *not* the right tool for:

* monitoring website uptime by probing it with HTTP requests
* collecting application performance metrics
* error tracking
* log aggregation
