# Status Badges

SITE_NAME provides status badges that you can embed in your READMEs, internal
dashboards, or public status pages. Each SITE_NAME badge reports the combined status of
checks tagged with a particular tag. There is also a catch-all badge that reflects
the status of all checks in a project.

![The "Badges" page](IMG_URL/badges.png)

The badges have public but hard-to-guess URLs. Badges do not expose information
other than the badge label and the aggregate status of their corresponding checks.
It is not possible to reverse-engineer ping URLs from badge URLs.

## Badge States

Each badge can be in one of the following three states:

* **up** (green) – all matching checks are up.
* **late** (orange) – at least one check is running late (but has not exceeded its grace time yet).
* **down** (red) – at least one check is currently down.

By default, SITE_NAME displays badge URLs that only report the
**up** and **down** states (and treat **late** as **up**). Using the "Badge states"
button, you can switch to alternate URLs that report all three states.

## Badge Formats

SITE_NAME offers badges in three different formats:

* SVG: returns an SVG document that you can use directly in an `<img>` element or
  a Markdown document.
* JSON: returns the badge label and the current status as a JSON document. Use this
  if you want to render the badge yourself. This can also serve as an integration
  point with a hosted status page: instruct your status page provider to monitor the
  badge URL and look for the keyword "up" in the returned data.
* Shields.io: returns the badge label and the current status as a
  Shields.io-compatible JSON document. See [Shields.io documentation](https://shields.io/endpoint)
  on how to use it. The main benefit of using Shields.io to generate badges is
  the extra visual styles and customization options that Shields.io supports.

## Badge for a Single Check

If you need a status badge for a specific check, assign the check a unique tag.
Then use that tag's badge.

