# Contributing

## Dependencies

On Debian:

```
sudo apt install libpq-dev
pip3 install -r requirements.txt
pip3 install markdown django
```

## Adding Documentation

1. Create the appropriate markdown page under `templates/docs`
2. Add the page to `/templates/front/base_docs.html`
3. Generate the HTML assets with `python3 manage.py render_docs` - note that the `manage.py` is in the root of the project.
