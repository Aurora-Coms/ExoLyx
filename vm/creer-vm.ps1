# ==========================================================================
#  ExoLyx - Création de la machine virtuelle VirtualBox (Windows)
#  Usage : double-cliquer sur creer-vm.bat
#          ou : powershell -ExecutionPolicy Bypass -File creer-vm.ps1 [-Iso C:\chemin\exolyx.iso]
# ==========================================================================
param(
    [string]$Iso = "",
    [string]$Nom = "ExoLyx",
    [int]$MemoireMo = 4096,
    [int]$Processeurs = 0,
    [int]$DisqueGo = 40,
    [switch]$Remplacer
)

$ErrorActionPreference = "Stop"
function VB { & $script:vbox @args; if ($LASTEXITCODE -ne 0) { Erreur "Échec de : VBoxManage $($args -join ' ')" } }
function Info($m)   { Write-Host "  > $m" -ForegroundColor Green }
function Alerte($m) { Write-Host "  ! $m" -ForegroundColor Yellow }
function Erreur($m) { Write-Host "  x $m" -ForegroundColor Red; Read-Host "Appuyez sur Entrée pour fermer"; exit 1 }

Write-Host ""
Write-Host "  ExoLyx - création de la machine virtuelle" -ForegroundColor Green
Write-Host "  -----------------------------------------"

# 1. Trouver VBoxManage
$vbox = $null
$candidats = @(
    "$env:VBOX_MSI_INSTALL_PATH\VBoxManage.exe",
    "$env:VBOX_INSTALL_PATH\VBoxManage.exe",
    "C:\Program Files\Oracle\VirtualBox\VBoxManage.exe",
    "C:\Program Files (x86)\Oracle\VirtualBox\VBoxManage.exe"
)
foreach ($c in $candidats) { if ($c -and (Test-Path $c)) { $vbox = $c; break } }
if (-not $vbox) {
    $cmd = Get-Command VBoxManage.exe -ErrorAction SilentlyContinue
    if ($cmd) { $vbox = $cmd.Source }
}
if (-not $vbox) { Erreur "VirtualBox introuvable. Installez-le depuis https://www.virtualbox.org puis relancez." }
Info "VirtualBox trouvé : $vbox"
$version = & $vbox --version
Info "Version : $version"

# 2. Trouver l'ISO (paramètre, sinon dossier du script, sinon Téléchargements)
if (-not $Iso) {
    $dossiers = @($PSScriptRoot, (Join-Path $env:USERPROFILE "Downloads"), (Join-Path $env:USERPROFILE "Téléchargements"), (Join-Path $env:USERPROFILE "Desktop"))
    foreach ($d in $dossiers) {
        if (Test-Path $d) {
            $f = Get-ChildItem -Path $d -Filter "exolyx*.iso" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
            if ($f) { $Iso = $f.FullName; break }
        }
    }
}
if ($Iso -and (Test-Path $Iso)) { Info "ISO : $Iso" }
else {
    Alerte "Aucune ISO ExoLyx trouvée (exolyx*.iso dans Téléchargements, Bureau ou ce dossier)."
    Alerte "La VM sera créée sans disque de démarrage ; relancez ce script quand l'ISO sera téléchargée."
    $Iso = ""
}

# 3. Réglages automatiques
if ($Processeurs -le 0) {
    $coeurs = (Get-CimInstance Win32_Processor | Measure-Object -Property NumberOfLogicalProcessors -Sum).Sum
    $Processeurs = [Math]::Max(2, [Math]::Min(4, [Math]::Floor($coeurs / 2)))
}
$ramTotaleMo = [Math]::Floor((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1MB)
if ($MemoireMo -gt ($ramTotaleMo / 2)) {
    $MemoireMo = [Math]::Max(2048, [Math]::Floor($ramTotaleMo / 2 / 256) * 256)
    Alerte "Mémoire ajustée à $MemoireMo Mo (la moitié de la RAM du PC)."
}

# 4. VM existante ?
$existe = (& $vbox list vms) -match "^`"$Nom`" "
if ($existe) {
    if ($Remplacer) {
        Alerte "La VM « $Nom » existe : suppression (-Remplacer)."
        try { & $vbox controlvm $Nom poweroff *> $null } catch { }
        Start-Sleep -Seconds 2
        & $vbox unregistervm $Nom --delete | Out-Null
    } else {
        if ($Iso) {
            Info "La VM « $Nom » existe déjà : je remplace seulement l'ISO."
            VB storageattach $Nom --storagectl "SATA" --port 1 --device 0 --type dvddrive --medium "$Iso"
            Info "Terminé. Démarrez « $Nom » dans VirtualBox."
        } else {
            Alerte "La VM « $Nom » existe déjà. Relancez avec -Remplacer pour la recréer."
        }
        Read-Host "Appuyez sur Entrée pour fermer"; exit 0
    }
}

# 5. Création
Info "Création de la VM « $Nom » ($MemoireMo Mo, $Processeurs processeurs, disque $DisqueGo Go)…"
VB createvm --name $Nom --ostype "ArchLinux_64" --register | Out-Null
$dossierVM = Split-Path -Parent ((& $vbox showvminfo $Nom --machinereadable | Select-String '^CfgFile=').ToString().Split('=',2)[1].Trim('"'))

VB modifyvm $Nom `
    --memory $MemoireMo --cpus $Processeurs `
    --firmware efi `
    --chipset ich9 --ioapic on --pae on --nested-paging on `
    --graphicscontroller vmsvga --vram 128 `
    --mouse usbtablet --keyboard ps2 --usb-xhci on `
    --audio-driver default --audio-controller hda --audio-enabled on --audio-out on `
    --nic1 nat --nictype1 virtio `
    --clipboard-mode bidirectional --drag-and-drop bidirectional `
    --rtc-use-utc on `
    --boot1 dvd --boot2 disk --boot3 none --boot4 none `
    --description "ExoLyx - Arch + Plasma, vert pomme"

# Disque (dynamique) + contrôleur SATA (AHCI)
$disque = Join-Path $dossierVM "$Nom.vdi"
VB createmedium disk --filename "$disque" --size ($DisqueGo * 1024) --format VDI --variant Standard | Out-Null
VB storagectl $Nom --name "SATA" --add sata --controller IntelAhci --portcount 2 --hostiocache on
VB storageattach $Nom --storagectl "SATA" --port 0 --device 0 --type hdd --medium "$disque" --nonrotational on --discard on
if ($Iso) {
    VB storageattach $Nom --storagectl "SATA" --port 1 --device 0 --type dvddrive --medium "$Iso"
} else {
    VB storageattach $Nom --storagectl "SATA" --port 1 --device 0 --type dvddrive --medium emptydrive
}

# Résolution d'écran de départ 1920x1080
& $vbox setextradata $Nom "VBoxInternal2/EfiGraphicsResolution" "1920x1080" | Out-Null

Write-Host ""
Info "VM « $Nom » créée."
Write-Host ""
Write-Host "  Pour tester :" -ForegroundColor Green
Write-Host "   1. Ouvrez VirtualBox, sélectionnez « $Nom », cliquez sur Démarrer."
Write-Host "   2. Choisissez « ExoLyx (live) » dans le menu de démarrage."
Write-Host "   3. Sur le bureau live, lancez « Installer ExoLyx »."
Write-Host "   4. Après l'installation, éteignez la VM, retirez l'ISO"
Write-Host "      (Configuration > Stockage) et redémarrez."
Write-Host ""
$lancer = Read-Host "Démarrer la VM maintenant ? (o/N)"
if ($lancer -match '^[oOyY]') { & $vbox startvm $Nom --type gui | Out-Null }
