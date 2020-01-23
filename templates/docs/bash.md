# Shell scripts

You can easily add SITE_NAME monitoring to a shell script. All you
have to do is make a HTTP request at the end of the script. curl and wget
are two common command line HTTP clients for that.

## Using curl

```bash hl_lines="12"
#!/bin/sh

# Exit immediately if any command exits with a non-zero status:
set -e

# Do the work here
echo "Pretending to to make backups..."
sleep 5
echo "Backup complete!"

# As the last thing, ping SITE_NAME using curl:
curl --retry 3 PING_URL
```

## Using wget

```bash hl_lines="12"
#!/bin/sh

# Exit immediately if any command exits with a non-zero status:
set -e

# Do the work here
echo "Pretending to to generate reports..."
sleep 5
echo "Report generation complete!"

# As the last thing, ping SITE_NAME using wget:
wget PING_URL -O /dev/null
```