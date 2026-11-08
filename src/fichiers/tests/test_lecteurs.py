import json
import unittest

import aide  # noqa: F401 (chemins)

import lecteurs

LSBLK_RECENT = json.dumps({"blockdevices": [
    {"name": "nvme0n1", "path": "/dev/nvme0n1", "label": None, "size": 512110190592, "fstype": None,
     "mountpoints": [None], "rm": False, "hotplug": False, "type": "disk", "uuid": None, "model": "Samsung SSD 980",
     "children": [
         {"name": "nvme0n1p1", "path": "/dev/nvme0n1p1", "label": None, "size": 536870912, "fstype": "vfat",
          "mountpoints": ["/boot"], "rm": False, "hotplug": False, "type": "part", "uuid": "AAAA-BBBB", "model": None},
         {"name": "nvme0n1p2", "path": "/dev/nvme0n1p2", "label": "exolyx", "size": 495000000000, "fstype": "btrfs",
          "mountpoints": ["/home", "/"], "rm": False, "hotplug": False, "type": "part", "uuid": "u2", "model": None},
         {"name": "nvme0n1p3", "path": "/dev/nvme0n1p3", "label": None, "size": 16000000000, "fstype": "swap",
          "mountpoints": ["[SWAP]"], "rm": False, "hotplug": False, "type": "part", "uuid": "u3", "model": None},
     ]},
    {"name": "sda", "path": "/dev/sda", "label": None, "size": 2000398934016, "fstype": None, "mountpoints": [None],
     "rm": False, "hotplug": False, "type": "disk", "uuid": None, "model": "WDC WD20EZRZ",
     "children": [{"name": "sda1", "path": "/dev/sda1", "label": "Données", "size": 2000397795328, "fstype": "ext4",
                   "mountpoints": [None], "rm": False, "hotplug": False, "type": "part", "uuid": "u4", "model": None}]},
    {"name": "sdb", "path": "/dev/sdb", "label": None, "size": 32015679488, "fstype": None, "mountpoints": [None],
     "rm": True, "hotplug": True, "type": "disk", "uuid": None, "model": "Cruzer Blade",
     "children": [{"name": "sdb1", "path": "/dev/sdb1", "label": None, "size": 32014630912, "fstype": "exfat",
                   "mountpoints": ["/run/media/moi/CLE USB"], "rm": True, "hotplug": True, "type": "part",
                   "uuid": "u5", "model": None}]},
    {"name": "loop0", "path": "/dev/loop0", "label": None, "size": 1000, "fstype": "squashfs",
     "mountpoints": ["/var/lib/snapd/snap/x"], "rm": False, "hotplug": False, "type": "loop", "uuid": None, "model": None},
]})

# util-linux < 2.37 : « mountpoint » au singulier, tailles en texte
LSBLK_ANCIEN = json.dumps({"blockdevices": [
    {"name": "sda", "label": None, "size": "128035676160", "fstype": None, "mountpoint": None, "rm": "1",
     "type": "disk", "model": "Clé",
     "children": [{"name": "sda1", "label": "SAUVEGARDE", "size": "128034627584", "fstype": "vfat",
                   "mountpoint": None, "rm": "1", "type": "part"}]},
]})

MOUNTS = """/dev/nvme0n1p2 / btrfs rw,relatime,subvol=/@ 0 0
/dev/nvme0n1p2 /home btrfs rw,relatime,subvol=/@home 0 0
/dev/sdb1 /run/media/moi/CLE\\040USB exfat rw,nosuid,nodev 0 0
proc /proc proc rw 0 0
/dev/vda / ext4 rw 0 0
"""


class TestLecteurs(unittest.TestCase):
    def test_mounts_octal(self):
        m = lecteurs.analyser_mounts(MOUNTS)
        self.assertEqual(m[2]["montage"], "/run/media/moi/CLE USB")
        self.assertEqual(m[2]["fstype"], "exfat")
        self.assertEqual(lecteurs.decoder_montage("/mnt/\\303\\251t\\303\\251"), "/mnt/été")

    def test_lsblk_recent(self):
        liste = lecteurs.analyser_lsblk(LSBLK_RECENT, lecteurs.analyser_mounts(MOUNTS))
        noms = [l["nom"] for l in liste]
        self.assertEqual(noms, ["Système", "Données", "Cruzer Blade 29,8 Go"])
        systeme, donnees, cle = liste
        self.assertEqual(systeme["montage"], "/")
        self.assertEqual(systeme["peripherique"], "/dev/nvme0n1p2")
        self.assertEqual(donnees["montage"], "")
        self.assertFalse(donnees["amovible"])
        self.assertTrue(cle["amovible"], "amovible hérité du disque parent")
        self.assertEqual(cle["montage"], "/run/media/moi/CLE USB")

    def test_lsblk_ancien(self):
        liste = lecteurs.analyser_lsblk(LSBLK_ANCIEN, [])
        self.assertEqual(len(liste), 1)
        self.assertEqual(liste[0]["nom"], "SAUVEGARDE")
        self.assertEqual(liste[0]["peripherique"], "/dev/sda1")
        self.assertEqual(liste[0]["taille"], 128034627584)
        self.assertTrue(liste[0]["amovible"])

    def test_type_complete_par_mounts(self):
        sans_type = json.dumps({"blockdevices": [{"name": "vda", "path": "/dev/vda", "size": 10, "fstype": None,
                                                   "mountpoints": ["/"], "type": "disk"}]})
        liste = lecteurs.analyser_lsblk(sans_type, lecteurs.analyser_mounts(MOUNTS))
        self.assertEqual([(l["nom"], l["fstype"]) for l in liste], [("Système", "ext4")])

    def test_json_invalide(self):
        self.assertEqual(lecteurs.analyser_lsblk("pas du json"), [])
        self.assertEqual(lecteurs.analyser_lsblk(""), [])

    def test_sortie_udisksctl(self):
        self.assertEqual(lecteurs.analyser_sortie_montage("Mounted /dev/sdb1 at /run/media/moi/CLE USB\n"),
                         "/run/media/moi/CLE USB")
        self.assertEqual(lecteurs.analyser_sortie_montage("Mounted /dev/sdc1 at /media/x.\n"), "/media/x")
        self.assertEqual(lecteurs.analyser_sortie_montage("Error"), "")


if __name__ == "__main__":
    unittest.main()
