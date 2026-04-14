param(
    [switch]$CliOnly
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$DistRoot = Join-Path $ProjectRoot "dist"
$BuildRoot = Join-Path $ProjectRoot "build"
$SpecRoot = Join-Path $ProjectRoot "spec"
$SrcRoot = Join-Path $ProjectRoot "src"

Set-Location $ProjectRoot

python -m pip install -r requirements.txt

if (Test-Path $BuildRoot) {
    Remove-Item -LiteralPath $BuildRoot -Recurse -Force
}

if (Test-Path $SpecRoot) {
    Remove-Item -LiteralPath $SpecRoot -Recurse -Force
}

$commonArgs = @(
    "--noconfirm",
    "--clean",
    "--distpath", $DistRoot,
    "--workpath", $BuildRoot,
    "--specpath", $SpecRoot,
    "--paths", $SrcRoot,
    "--collect-submodules", "textures_tool"
)

if (-not $CliOnly) {
    python -m PyInstaller `
        @commonArgs `
        --name "TexturesTool" `
        --windowed `
        --onefile `
        texture_resize_gui.py
}

python -m PyInstaller `
    @commonArgs `
    --name "TexturesToolCLI" `
    --console `
    --onefile `
    texture_resize_tool.py

Write-Host ""
Write-Host "Build complete."
Write-Host "Artifacts:"
if (-not $CliOnly) {
    Write-Host "  GUI: $DistRoot\\TexturesTool.exe"
}
Write-Host "  CLI: $DistRoot\\TexturesToolCLI.exe"
