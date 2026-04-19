param(
    [string]$SchemaDir = "schema/samsung_notes",
    [string]$OutputDir = "note_pipeline/input/samsung_notes/generated"
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command kaitai-struct-compiler -ErrorAction SilentlyContinue)) {
    throw "kaitai-struct-compiler was not found on PATH."
}

New-Item -ItemType Directory -Force $OutputDir | Out-Null
Remove-Item -Force -ErrorAction SilentlyContinue (Join-Path $OutputDir "samsung_*.py")
kaitai-struct-compiler -t python --outdir $OutputDir (Join-Path $SchemaDir "*.ksy")
