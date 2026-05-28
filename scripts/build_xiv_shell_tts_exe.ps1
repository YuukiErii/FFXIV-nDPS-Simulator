$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$ReleaseDir = Join-Path $Root "releases\windows"
$ArtifactDir = Join-Path $Root "artifacts"
$PyInstallerBuildDir = Join-Path $ArtifactDir "build\xiv_shell_tts_pyinstaller_build"
$SpecDir = Join-Path $ArtifactDir "specs"
$SkillMapPath = Join-Path $Root "data\ff14_job_skill_en_cn_map.json"

New-Item -ItemType Directory -Force -Path $ReleaseDir, $ArtifactDir, $PyInstallerBuildDir, $SpecDir | Out-Null

$Running = Get-Process -Name "XIVShellTTS" -ErrorAction SilentlyContinue
if ($Running) {
  $Running | Stop-Process -Force
}

.\.venv\Scripts\python.exe -m PyInstaller `
  --noconfirm `
  --clean `
  --onefile `
  --windowed `
  --name xiv_shell_tts `
  --distpath $ReleaseDir `
  --workpath $PyInstallerBuildDir `
  --specpath $SpecDir `
  --add-data "$SkillMapPath;data" `
  .\src\xiv_shell_tts\app.py

if ($LASTEXITCODE -ne 0) {
  throw "PyInstaller failed with exit code $LASTEXITCODE"
}

Write-Host "Built: $ReleaseDir\xiv_shell_tts.exe"
