#!/bin/sh
# Build invenux_<version>_amd64.deb from an extracted release folder (the one that
# holds invenux, _internal, invenux.desktop and invenux.png).
#   sh packaging/linux/build_deb.sh invenux-0.9.2-linux-x86_64 0.9.2 release
# The program goes to /opt/invenux, with /usr/bin/invenux, a menu entry and the icon;
# `sudo apt remove invenux` removes them and keeps each user's history and reports.
set -eu

src=${1:?release folder}
version=${2:?version}
out=${3:-.}

if [ ! -x "$src/invenux" ] || [ ! -d "$src/_internal" ]; then
    echo "$src is not an extracted invenux-<version>-linux-x86_64 folder." >&2
    exit 1
fi

root=$(mktemp -d)
trap 'rm -rf "$root"' EXIT

mkdir -p "$root/DEBIAN" "$root/opt/invenux" "$root/usr/bin" \
    "$root/usr/share/applications" "$root/usr/share/icons/hicolor/256x256/apps"
cp -R "$src/invenux" "$src/_internal" "$root/opt/invenux/"
ln -s /opt/invenux/invenux "$root/usr/bin/invenux"
sed "s|^Exec=.*|Exec=/opt/invenux/invenux|" "$src/invenux.desktop" > "$root/usr/share/applications/invenux.desktop"
install -m644 "$src/invenux.png" "$root/usr/share/icons/hicolor/256x256/apps/invenux.png"
chmod -R u+rwX,go+rX,go-w "$root"

size=$(du -sk "$root/opt" "$root/usr" | awk '{total += $1} END {print total}')
# The bundle carries its own Python and Qt; libc 2.35 is the oldest the build supports.
cat > "$root/DEBIAN/control" <<CONTROL
Package: invenux
Version: $version
Section: admin
Priority: optional
Architecture: amd64
Depends: libc6 (>= 2.35)
Installed-Size: $size
Maintainer: Lucas Motta <lucaswotta@users.noreply.github.com>
Homepage: https://github.com/lucaswotta/invenux
Description: Linux hardware inventory over SSH
 Reads processor, memory slots, disks, motherboard, BIOS, graphics, network
 and operating system from a spreadsheet of machines, over one read-only SSH
 connection per machine, and exports Excel, HTML and CSV reports.
CONTROL

cat > "$root/DEBIAN/postinst" <<'SCRIPT'
#!/bin/sh
set -e
if command -v update-desktop-database >/dev/null; then update-desktop-database -q /usr/share/applications || true; fi
if command -v gtk-update-icon-cache >/dev/null; then gtk-update-icon-cache -q -t /usr/share/icons/hicolor || true; fi
SCRIPT
cp "$root/DEBIAN/postinst" "$root/DEBIAN/postrm"
chmod 755 "$root/DEBIAN/postinst" "$root/DEBIAN/postrm"

mkdir -p "$out"
dpkg-deb --root-owner-group -Zxz --build "$root" "$out/invenux_${version}_amd64.deb"
