# Measuring Script Run Time

 Append `/start` to a ping URL and use it to signal when a job starts.
 After receiving a start signal, Healthchecks.io will show the check as "Started".
 It will store the "start" events and display the job execution times. The job
 execution times are calculated as the time gaps between adjacent "start" and
 "complete" events.

Signalling a start kicks off a separate timer: the job now **must** signal a
success within its configured "Grace Time", or it will get marked as "down".

Below is a code example in Python:

```python
import requests
URL = "PING_URL"


# "/start" kicks off a timer: if the job takes longer than
# the configured grace time, the check will be marked as "down"
try:
    requests.get(URL + "/start", timeout=5)
except requests.exceptions.RequestException:
    # If the network request fails for any reason, we don't want
    # it to prevent the main job from running
    pass


# TODO: run the job here
fib = lambda n: n if n < 2 else fib(n - 1) + fib(n - 2)
print("F(42) = %d" % fib(42))

# Signal success:
requests.get(URL)
```
