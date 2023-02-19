# Javascript

Below is a minimal example of making an HTTP request to SITE_NAME from Node.js.

```js
var https = require('https');
https.get('PING_URL').on('error', (err) => {
    console.log('Ping failed: ' + err)
});
```

Note: the "https" library executes requests asynchronously. If you send both "start"
and "success" signals, you can encounter a race condition where the "success" signal
arrives before the "start" signal. Avoid the race condition by using callbacks,
promises or the async/await feature. Here is an example that uses async/await and the
[axios](https://axios-http.com/) library:

```js
const axios = require("axios");

async function ping(url) {
    try {
        await axios.get(url, {timeout: 5000});
    } catch(error) {
        // Log the error and continue. A ping failure should
        // not prevent the job from running.
        console.error("Ping failed: " + error);
    }
}

async function runJob() {
    var pingUrl = "PING_URL";

    await ping(pingUrl + "/start");
    try {
        console.log("TODO: run the job here");

        await ping(pingUrl); // success
    } catch(error) {
        await ping(pingUrl + "/fail");
    }
}

runJob();
```

## Browser

You can also send pings from a browser environment. SITE_NAME sets the
`Access-Control-Allow-Origin:*` CORS header, so cross-domain AJAX requests work.

```js
var xhr = new XMLHttpRequest();
xhr.open('GET', 'PING_URL', true);
xhr.send(null);
```
