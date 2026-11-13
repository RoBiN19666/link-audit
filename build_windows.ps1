# Build the portable Windows executable.
# Usage:  powershell -ExecutionPolicy Bypass -File .\build_windows.ps1
param(
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
Set-Location $Root

Write-Host "== Link Audit portable build ==" -ForegroundColor Cyan
Write-Host "Project: $Root"

& $Python -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)"
if ($LASTEXITCODE -ne 0) {
    throw "Python 3.10+ is required."
}

& $Python -m pip install --disable-pip-version-check -r .\requirements-build.txt
if ($LASTEXITCODE -ne 0) {
    throw "Could not install build dependencies."
}

$pyiArgs = @(
    "-m", "PyInstaller",
    "--noconfirm", "--clean",
    "--onefile", "--windowed",
    "--name", "LinkAudit",
    "--icon", "$Root\assets\icon.ico",
    "--version-file", "$Root\assets\version_info.txt",
    "--add-data", "$Root\link_audit.py;.",
    "--collect-submodules", "streamlit",
    "--collect-data", "streamlit",
    "--collect-data", "altair",
    "--collect-all", "webview",
    "--collect-all", "pythonnet",
    "--collect-all", "clr_loader",
    "--collect-all", "cffi",
    "--copy-metadata", "streamlit",
    "--copy-metadata", "altair",
    "--copy-metadata", "pandas",
    "--copy-metadata", "numpy",
    "--copy-metadata", "pyarrow",
    "--copy-metadata", "tzdata",
    "--hidden-import", "streamlit.web.cli",
    "--hidden-import", "streamlit.runtime.scriptrunner.magic_funcs",
    "--hidden-import", "webview.platforms.edgechromium",
    "--hidden-import", "webview.platforms.winforms",
    "--hidden-import", "clr_loader",
    "--hidden-import", "pythonnet",
    "--exclude-module", "tensorflow",
    "--exclude-module", "torch",
    "--exclude-module", "matplotlib",
    "--exclude-module", "scipy",
    "--exclude-module", "IPython",
    "--exclude-module", "notebook",
    "--exclude-module", "streamlit.testing",
    "--exclude-module", "pydeck",
    "--distpath", "$Root\dist",
    "--workpath", "$Root\build",
    "--specpath", "$Root\build",
    "$Root\link_audit.py"
)

& $Python @pyiArgs
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed."
}

$exe = Join-Path $Root "dist\LinkAudit.exe"
if (-not (Test-Path -LiteralPath $exe)) {
    throw "EXE was not created: $exe"
}

$hash = (Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash
$size = [math]::Round((Get-Item -LiteralPath $exe).Length / 1MB, 1)
Write-Host ""
Write-Host "OK: $exe" -ForegroundColor Green
Write-Host "Size: $size MB"
Write-Host "SHA256: $hash"
