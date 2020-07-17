# PowerShell

 You can use [PowerShell](https://msdn.microsoft.com/en-us/powershell/mt173057.aspx)
 and Windows Task Scheduler to automate various tasks on a Windows system.
 From within a PowerShell script it is also easy to ping SITE_NAME.

Here is a simple PowerShell script that pings SITE_NAME. When scheduled to
run with Task Scheduler, it will essentially just send regular "I'm alive" messages.
You can of course extend it to do more things.

```powershell
# inside a PowerShell script:
Invoke-RestMethod PING_URL
```

Save the above to e.g. `C:\Scripts\healthchecks.ps1`.
Then use the following command in a Scheduled Task to run the script:

```bat
powershell.exe -ExecutionPolicy bypass -File C:\Scripts\healthchecks.ps1
```

In simple cases, you can also pass the script to PowerShell directly,
using the "-command" argument:

```bat
# Without an underlying script, passing the command to PowerShell directly:
powershell.exe -command &{Invoke-RestMethod PING_URL}
```
