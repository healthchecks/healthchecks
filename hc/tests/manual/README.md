# Manual Email Slug Test Files

This folder contains HTML test files used to manually verify the `/email-slug/` endpoint.

## Files

- `email-slug-test2.html`: Basic form to submit an email and ping a check using a slug.
- `email-slug-test3.html`: Variation of the form for extended testing.

## How to Use

1. Start the Django server:
   ```bash
   python manage.py runserver
2. Open these .html files in your browser (right-click → "Open With Browser").

3. Enter an email like test@example.com, click "Send Ping".

4. Check your terminal logs — you should see the ping logged with the correct slug.
