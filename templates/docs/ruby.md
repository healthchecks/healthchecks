# Ruby

Below is an example of making a HTTP request to SITE_NAME from Ruby.

```ruby
require 'net/http'
require 'uri'

Net::HTTP.get(URI.parse('PING_URL'))
```