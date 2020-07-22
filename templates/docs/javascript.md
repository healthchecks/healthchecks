# Javascript

Below is an example of making a HTTP request to SITE_NAME from Node.js.

```js
var https = require('https');
https.get('PING_URL').on('error', (err) => {
    console.log('Ping failed: ' + err)
});
```

You can also send pings from a browser environment. SITE_NAME sets the
`Access-Control-Allow-Origin:*` CORS header, so cross-domain AJAX requests work.

```js
var xhr = new XMLHttpRequest();
xhr.open('GET', 'PING_URL', true);
xhr.send(null);
```
