# Contributing

I'm open to feature suggestions and happy to review code contributions.
If you are planning to contribute something larger than a small, straightforward
bugfix, please open an issue so we can discuss it first. Otherwise you are risking a 
"no" or a "yes, but let's do it differently" to an already implemented feature.

## Code Style

* Format your Python code with [black](https://black.readthedocs.io/en/stable/).
* Prefer simplicity over cleverness.
* If you are fixing a bug or adding a feature, add a test. Run tests before 
  submitting pull requests.

## Adding Documentation

This project uses the Markdown format for documentation. Use the `render_docs` 
management command to generate the HTML version of the documentation. To add a new
documentation page:

1. Create the appropriate .md file under `templates/docs`
2. Generate the HTML version with `./manage.py render_docs` 
3. Add the page to the navigation in `/templates/front/docs_single.html`

## Developing a New Integration

The best way to build a new integration is to pick a similar existing integration
as a starting point for the new integration and replicate every aspect of it.
You will need to make changes in the following files:

* Add a new class in `/hc/api/transports.py`.
* Add a new notification template in `/templates/integrations/`.
* Write testcases for the new transport class in `/hc/api/tests/test_notify_<kind>.py`.
* Update `CHANNEL_KINDS` in `/hc/api/models.py`.
* Update `Channel.transport()` in `/hc/api/models.py`.
* Create a view for provisioning the new integration in `/hc/front/views.py`.
* Write a HTML template for the new view in `/templates/front/add_<kind>.py`, and
  prepare any supporting illustrations in `/static/img/integrations/`.
* Add a route for the new view in `/hc/front/urls.py`.
* Write testcases for the new view in `/hc/font/tests/test_add_<kind>.py`.
* Update `/templates/front/channels.html` – add a new section in the list of available
  integrations, make sure an existing integration is displayed nicely.
* Update `/templates/front/event_summary.html` to make sure notifications sent to the
  new integration are displayed nicely.
* Add a logo in `/static/img/integrations/`.
* Update the icon font (it's a little tricky to do, I can take care of that).

If you intend to contribute the new integration to the Healthchecks project
(as opposed to maintaining it in a separate fork), please open an issue and
discuss it first.
