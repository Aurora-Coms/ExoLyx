#!/usr/bin/env bash
# ExoLyx - création de la machine virtuelle VirtualBox (Linux / macOS)
# Usage : ./creer-vm.sh [chemin/exolyx.iso]
set -euo pipefail
NOM="${NOM:-ExoLyx}"; MEM="${MEM:-4096}"; CPU="${CPU:-2}"; DISQUE_GO="${DISQUE_GO:-40}"
ISO="${1:-$(ls -t "$HOME"/Téléchargements/exolyx*.iso "$HOME"/Downloads/exolyx*.iso 2>/dev/null | head -1 || true)}"
command -v VBoxManage >/dev/null || { echo "VirtualBox introuvable."; exit 1; }
if VBoxManage list vms | grep -q "^\"$NOM\" "; then
  [ -n "$ISO" ] && VBoxManage storageattach "$NOM" --storagectl SATA --port 1 --device 0 --type dvddrive --medium "$ISO"
  echo "La VM $NOM existe déjà (ISO mise à jour si fournie)."; exit 0
fi
VBoxManage createvm --name "$NOM" --ostype ArchLinux_64 --register
DOSSIER=$(dirname "$(VBoxManage showvminfo "$NOM" --machinereadable | sed -n 's/^CfgFile="\(.*\)"$/\1/p')")
VBoxManage modifyvm "$NOM" --memory "$MEM" --cpus "$CPU" --firmware efi --chipset ich9 --ioapic on \
  --graphicscontroller vmsvga --vram 128 --mouse usbtablet --usb-xhci on \
  --audio-driver default --audio-controller hda --audio-enabled on --audio-out on \
  --nic1 nat --nictype1 virtio --clipboard-mode bidirectional --rtc-use-utc on --boot1 dvd --boot2 disk
VBoxManage createmedium disk --filename "$DOSSIER/$NOM.vdi" --size $((DISQUE_GO*1024)) --format VDI
VBoxManage storagectl "$NOM" --name SATA --add sata --controller IntelAhci --portcount 2
VBoxManage storageattach "$NOM" --storagectl SATA --port 0 --device 0 --type hdd --medium "$DOSSIER/$NOM.vdi" --nonrotational on --discard on
VBoxManage storageattach "$NOM" --storagectl SATA --port 1 --device 0 --type dvddrive --medium "${ISO:-emptydrive}"
VBoxManage setextradata "$NOM" VBoxInternal2/EfiGraphicsResolution 1920x1080
echo "VM $NOM créée. Démarrage : VBoxManage startvm $NOM"
