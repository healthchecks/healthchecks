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
3. Add the page to the navigation in `/templates/front/base_docs.html`
