param(
    [Parameter(Mandatory = $true)]
    [string[]]$Book,

    [string]$VerseAudioRoot = "..\..\audio\kjv",
    [string]$Output = "..\..\audio\kjv-chapters",
    [string]$PublicBaseUrl = "https://app-developerz.github.io/audio/kjv-chapters",
    [int]$GapMilliseconds = 180,
    [double]$SilenceThresholdDb = -45,
    [int]$MinimumSilenceMilliseconds = 100,
    [int]$KeepSilenceMilliseconds = 80,
    [string]$Bitrate = "48k",
    [switch]$Overwrite,
    [switch]$ReinstallDependencies
)

$ErrorActionPreference = "Stop"

$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Builder = Join-Path $ScriptRoot "build_chapter_narration.py"
$VenvDirectory = Join-Path $ScriptRoot ".venv"
$VenvPython = Join-Path $VenvDirectory "Scripts\python.exe"
$DataRoot = Join-Path $ScriptRoot "..\..\data"

if (-not (Test-Path $Builder)) {
    throw "Chapter builder not found: $Builder"
}

if (-not (Test-Path (Join-Path $DataRoot "index.json"))) {
    throw "Bible data was not found at: $DataRoot"
}

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw "Python launcher 'py' was not found."
}

if (-not (Test-Path $VenvPython)) {
    Write-Host "Creating the local Python environment..." -ForegroundColor Cyan
    & py -3.13 -m venv $VenvDirectory

    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $VenvPython)) {
        & py -m venv $VenvDirectory
    }

    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $VenvPython)) {
        throw "Unable to create the local Python environment."
    }
}

$env:PYTHONNOUSERSITE = "1"

$dependencyReady = $false

if (-not $ReinstallDependencies) {
    & $VenvPython -c "import imageio_ffmpeg; print('imageio-ffmpeg OK:', imageio_ffmpeg.__file__)"
    $dependencyReady = ($LASTEXITCODE -eq 0)
}

if (-not $dependencyReady) {
    Write-Host "Installing FFmpeg dependency..." -ForegroundColor Cyan

    & $VenvPython -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to update pip."
    }

    & $VenvPython -m pip install --upgrade --force-reinstall imageio-ffmpeg
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to install imageio-ffmpeg."
    }
}

Write-Host "Verifying Python 3.13-compatible chapter builder..." -ForegroundColor Cyan
& $VenvPython -c "import sys, imageio_ffmpeg; print('Python:', sys.executable); print('FFmpeg:', imageio_ffmpeg.get_ffmpeg_exe())"

if ($LASTEXITCODE -ne 0) {
    throw "The local Python environment could not load imageio-ffmpeg."
}

$arguments = @(
    $Builder,
    "--data-root", (Resolve-Path $DataRoot).Path,
    "--verse-audio-root", $VerseAudioRoot,
    "--output", $Output,
    "--public-base-url", $PublicBaseUrl,
    "--gap-ms", $GapMilliseconds,
    "--silence-threshold-db", $SilenceThresholdDb,
    "--minimum-silence-ms", $MinimumSilenceMilliseconds,
    "--keep-silence-ms", $KeepSilenceMilliseconds,
    "--bitrate", $Bitrate
)

foreach ($item in $Book) {
    $arguments += @("--book", $item)
}

if ($Overwrite) {
    $arguments += "--overwrite"
}

Write-Host "Building seamless chapter narration..." -ForegroundColor Green
& $VenvPython @arguments

if ($LASTEXITCODE -ne 0) {
    throw "Chapter narration builder exited with code $LASTEXITCODE."
}

Write-Host "Chapter narration build completed successfully." -ForegroundColor Green
