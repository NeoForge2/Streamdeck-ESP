# Installe l'appli compagnon Stream Deck au demarrage de Windows :
# cree un raccourci dans le dossier "Demarrage" qui lance l'icone de
# barre des taches (tray.py) silencieusement, sans fenetre de console.
#
# A executer depuis le dossier pc-app :
#   powershell -ExecutionPolicy Bypass -File install_startup.ps1

$ErrorActionPreference = "Stop"

$pcAppDir = $PSScriptRoot
$pythonwPath = (Get-Command pythonw.exe -ErrorAction SilentlyContinue).Source
if (-not $pythonwPath) {
    Write-Error "pythonw.exe introuvable dans le PATH. Verifiez votre installation Python."
    exit 1
}

$startupDir = [Environment]::GetFolderPath("Startup")
$shortcutPath = Join-Path $startupDir "Stream Deck.lnk"

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $pythonwPath
$shortcut.Arguments = "-m streamdeck_companion.tray"
$shortcut.WorkingDirectory = $pcAppDir
$shortcut.Description = "Stream Deck - recepteur d'actions (icone barre des taches)"
$shortcut.Save()

Write-Host "Raccourci cree : $shortcutPath"
Write-Host "L'appli demarrera automatiquement a la prochaine connexion Windows."
Write-Host "Pour la lancer tout de suite sans redemarrer : pythonw -m streamdeck_companion.tray"
