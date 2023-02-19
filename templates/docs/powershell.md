# PowerShell

 You can use [PowerShell](https://docs.microsoft.com/en-us/powershell/scripting/overview?view=powershell-7.2)
 and Windows Task Scheduler to automate various tasks on a Windows system.
 From within a PowerShell script, it is also easy to ping SITE_NAME.

Here is a simple PowerShell script that pings SITE_NAME. When scheduled to
run with Task Scheduler, it will send regular "I'm alive" messages.
Of course, you can extend it to do more things.

```powershell
# Save this in a file with a .ps1 extension, e.g. C:\Scripts\healthchecks.ps1
# The command to run it:
#     powershell.exe -ExecutionPolicy bypass -File C:\Scripts\healthchecks.ps1
#
Invoke-RestMethod PING_URL
```

You can send additional diagnostic information in HTTP POST requests:

```powershell
Invoke-RestMethod -Uri PING_URL -Method Post -Body "temperature=-7"
```

For other parameters, you can use in the `Invoke-RestMethod` cmdlet,
see the official [Invoke-RestMethod documentation](https://docs.microsoft.com/en-us/powershell/module/microsoft.powershell.utility/invoke-restmethod?view=powershell-7.2).

As an alternative to putting the script in a .ps1 file, you can also pass it
to PowerShell directly, using the "-Command" argument:

```bat
# Pass the command to PowerShell directly:
powershell.exe -Command "&{Invoke-RestMethod PING_URL}"
```

