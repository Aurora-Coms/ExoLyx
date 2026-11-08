# Surcharges appliquées au profiledef.sh de « releng » par scripts/build-iso.sh
iso_name="exolyx"
iso_label="EXOLYX_$(date --date="@${SOURCE_DATE_EPOCH:-$(date +%s)}" +%Y%m)"
iso_publisher="ExoLyx <https://github.com/Aurora-Coms/ExoLyx>"
iso_application="ExoLyx - live et installation"
iso_version="$(date --date="@${SOURCE_DATE_EPOCH:-$(date +%s)}" +%Y.%m.%d)"
install_dir="arch"
airootfs_image_type="squashfs"
airootfs_image_tool_options=('-comp' 'xz' '-Xbcj' 'x86' '-b' '1M' '-Xdict-size' '1M')
file_permissions+=(
  ["/etc/shadow"]="0:0:400"
  ["/etc/gshadow"]="0:0:400"
  ["/etc/sudoers.d/10-exolyx-live"]="0:0:440"
)
