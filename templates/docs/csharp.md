# C\#

Below is an example of making an HTTP request to SITE_NAME from C#.

```csharp
try
{
    using (var client = new System.Net.Http.HttpClient())
    {
        client.Timeout = System.TimeSpan.FromSeconds(10);
        client.GetAsync("PING_URL").Wait();
    }
}
catch (System.Exception ex)
{
    System.Console.WriteLine($"Ping failed: {ex.Message}");
}
```