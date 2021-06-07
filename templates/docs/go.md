# Go

Below is an example of making an HTTP request to SITE_NAME from Go.

```go
package main

import "fmt"
import "net/http"
import "time"

func main() {
    var client = &http.Client{
        Timeout: 10 * time.Second,
    }

    resp, err := client.Head("PING_URL")
    if err != nil {
        fmt.Printf("%s", err)
    }
    resp.Body.Close()
}

```
