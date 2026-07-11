$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$ReleaseDir = Join-Path $Root "releases\windows"
$ArtifactDir = Join-Path $Root "artifacts"
$PyInstallerBuildDir = Join-Path $ArtifactDir "build\ffxiv_ndps_pyinstaller_build"
$SpecDir = Join-Path $ArtifactDir "specs\ffxiv_ndps_pyinstaller_spec"
$SkillMapPath = Join-Path $Root "data\ff14_job_skill_en_cn_map.json"
$SkillLineDir = Join-Path $Root "examples/skill_lines"
$GameTxt = Join-Path $Root "src\ffxiv_ndps_simulator\game.txt"
$StatFnsTxt = Join-Path $Root "src\ffxiv_ndps_simulator\stat_fns.txt"
$DamageCalTxt = Join-Path $Root "src\ffxiv_ndps_simulator\damage_cal.txt"
$IconPath = Join-Path $Root "src\ffxiv_ndps_simulator\ffxiv_ndps.ico"

New-Item -ItemType Directory -Force -Path $ReleaseDir, $ArtifactDir, $PyInstallerBuildDir, $SpecDir | Out-Null

$Running = Get-Process -Name "FFXIVPersonalNDPS" -ErrorAction SilentlyContinue
if ($Running) {
  $Running | Stop-Process -Force
}

.\.venv\Scripts\python.exe -m PyInstaller `
  --noconfirm `
  --clean `
  --onefile `
  --console `
  --name ffxiv_personal_ndps `
  --distpath $ReleaseDir `
  --workpath $PyInstallerBuildDir `
  --specpath $SpecDir `
  --paths ".\src\ffxiv_ndps_simulator" `
  --add-data "$SkillMapPath;data" `
  --add-data "$SkillLineDir;examples/skill_lines" `
  --add-data "$GameTxt;ffxiv_ndps_simulator" `
  --add-data "$StatFnsTxt;ffxiv_ndps_simulator" `
  --add-data "$DamageCalTxt;ffxiv_ndps_simulator" `
  --add-data "$IconPath;." `
  --icon "$IconPath" `
  .\src\ffxiv_ndps_simulator\sim.py

if ($LASTEXITCODE -ne 0) {
  throw "PyInstaller failed with exit code $LASTEXITCODE"
}

Write-Host "Built: $ReleaseDir\ffxiv_personal_ndps.exe"
Write-Host "Verify with: $ReleaseDir\ffxiv_personal_ndps.exe --self-test"
