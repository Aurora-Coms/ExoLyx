@echo off
chcp 65001 >nul
rem ExoLyx - lance creer-vm.ps1 sans changer la politique d'exécution du système
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0creer-vm.ps1" %*
