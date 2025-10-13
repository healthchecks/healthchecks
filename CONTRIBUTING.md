# Contributing

I'm open to feature suggestions and happy to review code contributions.
If you are planning to contribute something larger than a small, straightforward
bugfix, please open an issue so we can discuss it first. Otherwise you are risking a
"no" or a "yes, but let's do it differently" to an already implemented feature.

## AI Policy

I do not accept content generated or touched up by AI tools. Do not
submit pull requests or issues produced with the help of LLMs or code generation
assistants, they will be closed with no discussion. Do not write emails
generated or rewritten by LLMs, they will be marked as spam.

## Code Style

* Format your Python code with [ruff](https://docs.astral.sh/ruff/).
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

Before starting work on a new integration, please open an issue and
discuss it first. We use several criteria when deciding whether to work on an
integration or accept a PR:

* Most important: is there substantial end-user (ideally, paying or would-be-paying
  end user) interest, across GitHub issues, private emails, social media?
* Would it be fun to work on?
* Is the service we are integrating with developer-friendly? Does it have an open
  and well-documented API? Can we develop and test the integration while avoiding
  sales calls, contract signing, paid subscriptions?
* Does the new integration enable something that is otherwise not possible (or is
  very inconvenient) via webhooks or email?

The best way to build a new integration is to pick a similar existing integration
as a starting point for the new integration and replicate every aspect of it.
You will need to make changes in the following files:

* In `/hc/integrations/`, copy an existing integration to a new directory
* Edit the transport class in `/hc/integrations/<kind>/transport.py`.
* Edit the notification template(s) in `/hc/integrations/<kind>/templates/`.
* Write testcases for the transport class in
  `/hc/integrations/<kind>/tests/test_notify.py`.
* Update `TRANSPORTS` in `/hc/api/models.py`.
* Edit the view(s) for provisioning the integration in
  `/hc/integrations/<kind>/views.py`.
* Write a HTML template for the new view in
  `/hc/integrations/<kind>/templates/</add_<kind>.py`, and prepare any supporting
  illustrations in `/hc/integrations/<kind>/static/img/`.
* Edit routes for the new view(s) in `/hc/integrations/<kind>/urls.py`.
* Include the new integration's urls.py in `/hc/urls.py`
* Write testcases for the new view in `/hc/integrations/<kind>/tests/test_add.py`.
* Update `/templates/front/channels.html` – add a new section in the list of available
  integrations, make sure an existing integration is displayed nicely.
* Update `/templates/front/event_summary.html` to make sure notifications sent to the
  new integration are displayed nicely.
* Add a logo in `/hc/integrations/<kind>static/img/`.
* Update the icon font (it's a little tricky to do, I can take care of that).
