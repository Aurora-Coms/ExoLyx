# Machine virtuelle ExoLyx (VirtualBox)

## Windows
1. Téléchargez l'ISO ExoLyx (onglet **Actions** du dépôt → dernier build réussi → *Artifacts* → `exolyx-iso`), dézippez-la dans **Téléchargements**.
2. Double-cliquez sur `creer-vm.bat`.
3. Le script crée la VM **ExoLyx** : UEFI, 4 Go de RAM (ou la moitié de celle du PC), 2 à 4 processeurs, disque SSD virtuel de 40 Go, carte graphique VMSVGA 128 Mo, son, presse-papiers partagé, souris tablette.
4. Répondez « o » pour la démarrer.

Options (PowerShell) :
```powershell
.\creer-vm.ps1 -Iso "D:\isos\exolyx-2026.11.iso"   # ISO précise
.\creer-vm.ps1 -MemoireMo 8192 -Processeurs 4      # plus de puissance
.\creer-vm.ps1 -Remplacer                          # supprime et recrée la VM
```
Relancer le script quand la VM existe déjà **remplace seulement l'ISO** (pratique à chaque nouveau build).

## Linux / macOS
```bash
./creer-vm.sh ~/Téléchargements/exolyx-2026.11.iso
```

## Conseils
- Laissez l'**accélération 3D désactivée** : Plasma est plus stable sans elle dans VirtualBox.
- Après l'installation : éteignez, retirez l'ISO (*Configuration → Stockage*), redémarrez.
- Les instantanés VirtualBox (*Machine → Prendre un instantané*) permettent de revenir à une VM fraîchement installée.
