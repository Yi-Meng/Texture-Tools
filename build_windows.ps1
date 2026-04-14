param(
    [switch]$CliOnly
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
& (Join-Path $ScriptDir "scripts\build_windows.ps1") -CliOnly:$CliOnly
