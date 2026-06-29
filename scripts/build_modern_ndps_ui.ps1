$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$AppRoot = Join-Path $Root "apps\ndps-ui"
$ReleaseRoot = Join-Path $Root "releases\windows"
$ModernReleaseDir = Join-Path $ReleaseRoot "ffxiv_personal_ndps_modern"
$ArtifactDir = Join-Path $Root "artifacts"
$BackendBuildDir = Join-Path $ArtifactDir "build\ndps_ui_backend_build"
$BackendDistDir = Join-Path $ArtifactDir "build\ndps_ui_backend_dist"
$SpecDir = Join-Path $ArtifactDir "specs\ndps_ui_backend_spec"
$BackendExe = Join-Path $BackendDistDir "ndps_backend.exe"
$NodeExeCandidates = @(
  (Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe"),
  "node.exe"
)

function Resolve-NodeExe {
  foreach ($Candidate in $NodeExeCandidates) {
    $Command = Get-Command $Candidate -ErrorAction SilentlyContinue
    if ($Command) {
      return $Command.Source
    }
  }
  throw "Could not find node.exe. Install Node.js or run inside the Codex workspace runtime."
}

function Remove-DirectoryInside {
  param(
    [string]$Path,
    [string]$Parent
  )
  if (-not (Test-Path $Path)) {
    return
  }
  $ResolvedPath = (Resolve-Path $Path).Path
  $ResolvedParent = (Resolve-Path $Parent).Path
  if (-not $ResolvedPath.StartsWith($ResolvedParent, [StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to remove path outside $ResolvedParent`: $ResolvedPath"
  }
  Remove-Item -LiteralPath $ResolvedPath -Recurse -Force
}

Set-Location $Root
New-Item -ItemType Directory -Force -Path $ReleaseRoot, $ArtifactDir, $BackendBuildDir, $BackendDistDir, $SpecDir | Out-Null

$Running = Get-Process -Name "ffxiv_personal_ndps_modern" -ErrorAction SilentlyContinue
if ($Running) {
  $Running | Stop-Process -Force
}

$SkillMapPath = Join-Path $Root "data\ff14_job_skill_en_cn_map.json"
$SkillLineDir = Join-Path $Root "examples\skill_lines"
$GameTxt = Join-Path $Root "src\ffxiv_ndps_simulator\game.txt"
$StatFnsTxt = Join-Path $Root "src\ffxiv_ndps_simulator\stat_fns.txt"
$DamageCalTxt = Join-Path $Root "src\ffxiv_ndps_simulator\damage_cal.txt"

.\.venv\Scripts\python.exe -m PyInstaller `
  --noconfirm `
  --clean `
  --onefile `
  --console `
  --name ndps_backend `
  --distpath $BackendDistDir `
  --workpath $BackendBuildDir `
  --specpath $SpecDir `
  --paths ".\src\ffxiv_ndps_simulator" `
  --collect-submodules ama_xiv_combat_sim `
  --add-data "$SkillMapPath;data" `
  --add-data "$SkillLineDir;examples\skill_lines" `
  --add-data "$GameTxt;ffxiv_ndps_simulator" `
  --add-data "$StatFnsTxt;ffxiv_ndps_simulator" `
  --add-data "$DamageCalTxt;ffxiv_ndps_simulator" `
  .\scripts\run_ndps_simulation.py

if ($LASTEXITCODE -ne 0) {
  throw "PyInstaller backend build failed with exit code $LASTEXITCODE"
}

if (-not (Test-Path $BackendExe)) {
  throw "Backend executable was not produced: $BackendExe"
}

$NodeExe = Resolve-NodeExe
Set-Location $AppRoot
& $NodeExe ".\node_modules\vite\bin\vite.js" build
if ($LASTEXITCODE -ne 0) {
  throw "Vite build failed with exit code $LASTEXITCODE"
}

Set-Location $Root

$ElectronDist = Join-Path $AppRoot "node_modules\electron\dist"
if (-not (Test-Path (Join-Path $ElectronDist "electron.exe"))) {
  throw "Electron runtime is missing. Run dependency installation for apps\ndps-ui first."
}

if (-not (Test-Path $ModernReleaseDir)) {
  Copy-Item -Path $ElectronDist -Destination $ModernReleaseDir -Recurse
  Rename-Item -LiteralPath (Join-Path $ModernReleaseDir "electron.exe") -NewName "ffxiv_personal_ndps_modern.exe"
} else {
  Get-ChildItem -LiteralPath $ElectronDist | Where-Object { $_.Name -ne "resources" -and $_.Name -ne "electron.exe" } | ForEach-Object {
    $Destination = Join-Path $ModernReleaseDir $_.Name
    if ($_.PSIsContainer) {
      Remove-DirectoryInside -Path $Destination -Parent $ModernReleaseDir
    }
    Copy-Item -LiteralPath $_.FullName -Destination $Destination -Recurse -Force
  }
  if (-not (Test-Path (Join-Path $ModernReleaseDir "ffxiv_personal_ndps_modern.exe"))) {
    Copy-Item -LiteralPath (Join-Path $ElectronDist "electron.exe") -Destination (Join-Path $ModernReleaseDir "ffxiv_personal_ndps_modern.exe") -Force
  }
}

$ResourcesDir = Join-Path $ModernReleaseDir "resources"
$AppPackageDir = Join-Path $ResourcesDir "app"
$BackendPackageDir = Join-Path $ResourcesDir "backend"
Remove-DirectoryInside -Path $AppPackageDir -Parent $ModernReleaseDir
Remove-DirectoryInside -Path $BackendPackageDir -Parent $ModernReleaseDir
New-Item -ItemType Directory -Force -Path $AppPackageDir, $BackendPackageDir | Out-Null

Copy-Item -Path (Join-Path $AppRoot "dist") -Destination (Join-Path $AppPackageDir "dist") -Recurse
Copy-Item -Path (Join-Path $AppRoot "electron") -Destination (Join-Path $AppPackageDir "electron") -Recurse
Copy-Item -Path $BackendExe -Destination (Join-Path $BackendPackageDir "ndps_backend.exe") -Force
Copy-Item -Path (Join-Path $AppRoot "public\favicon.svg") -Destination (Join-Path $AppPackageDir "favicon.svg") -Force

$PackageJson = @{
  name = "ffxiv-ndps-modern"
  version = "0.1.0"
  main = "electron/main.cjs"
  private = $true
} | ConvertTo-Json -Depth 3
$PackageJson | Set-Content -Path (Join-Path $AppPackageDir "package.json") -Encoding UTF8

$ReleaseNote = @"
# FFXIV Personal nDPS Modern UI

Run `ffxiv_personal_ndps_modern.exe` to open the React/Electron desktop UI.

This package includes:

- the built modern UI under `resources\app`
- the packaged Python JSON backend under `resources\backend\ndps_backend.exe`
- the Electron runtime files required by the desktop shell

Use the legacy stable simulator GUI at `..\ffxiv_personal_ndps.exe` if you need the older Tk interface or command-line self-test.
"@
$ReleaseNote | Set-Content -Path (Join-Path $ModernReleaseDir "README.md") -Encoding UTF8

Write-Host "Built modern UI package: $ModernReleaseDir"
Write-Host "Run: $ModernReleaseDir\ffxiv_personal_ndps_modern.exe"
