# Go

## net/http

Below is an example of making an HTTP request to SITE_NAME from Go using stdlib's `net/http`.

```go
package main

import "fmt"
import "net/http"
import "time"

func main() {
    var client = &http.Client{
        Timeout: 10 * time.Second,
    }

    _, err := client.Head("PING_URL")
    if err != nil {
        fmt.Printf("%s", err)
    }
}

```

## gitlab.com/etke.cc/go/healthchecks

Below is an example of using [gitlab.com/etke.cc/go/healthchecks](https://gitlab.com/etke.cc/go/healthchecks) library, that has the following features:

* Highly configurable: `WithHTTPClient()`, `WithBaseURL()`, `WithUserAgent()`, `WithErrLog()`, `WithCheckUUID()`, `WithAutoProvision()`, etc.
* Automatic determination of HTTP method (`POST`, `HEAD`) based on body existence
* Auto mode: just call `client.Auto(time.Duration)` and client will send `Success()` request automatically with specified frequency
* Global mode: init client once with `healthchecks.New()`, and access it from anywhere by calling `healthchecks.Global()`

```go
package main

import "gitlab.com/etke.cc/go/healthchecks/v2"

func main() {
    var client = healthchecks.New(
        healthchecks.WithCheckUUID("CHECK_UUID")
    )
    client.Success()
}
```
