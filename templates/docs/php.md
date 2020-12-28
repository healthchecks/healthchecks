# PHP

Below is an example of making an HTTP request to SITE_NAME from PHP.

```php
file_get_contents('PING_URL');
```

If you would like to setup timeout and retry options, as discussed in the
[reliability tips section](../reliability_tips/), there is a
[curl package](https://www.phpcurlclass.com/) available that lets you do that easily:

```php
use Curl\Curl;

$curl = new Curl();
$curl->setRetry(20);
$curl->setTimeout(5);
$curl->get('PING_URL');
```

Note: this code does not throw any exceptions.
