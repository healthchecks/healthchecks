# C\#

Below is an example of making an HTTP request to SITE_NAME from C#.

```csharp
using (var client = new System.Net.WebClient())
{
       client.DownloadString("PING_URL");
}
```