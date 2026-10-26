#!/bin/sh
# Staging only. No service, routing or network changes.
set -eu
cd "$(dirname "$0")/../.."
root=$(pwd)
[ "$(uname -m)" = aarch64 ] || { echo 'BŁĄD: Wymagany system Linux ARM64.' >&2; exit 1; }
for tool in python3 ldd systemctl; do command -v "$tool" >/dev/null || { echo "BŁĄD: Brak $tool. Przygotuj tę zależność przed instalacją offline." >&2; exit 1; }; done
python3 - "$root" <<'PY'
import hashlib,json,pathlib,sys
root=pathlib.Path(sys.argv[1]);manifest=json.loads((root/'FILES-SHA256.json').read_text())
for name,expected in manifest.items():
 path=root/name
 if not path.is_relative_to(root) or '..' in pathlib.Path(name).parts or hashlib.sha256(path.read_bytes()).hexdigest()!=expected:raise SystemExit('BŁĄD: uszkodzona paczka: '+name)
print('Sumy plików poprawne.')
PY
export LD_LIBRARY_PATH="$root/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
ldd "$root/bin/jerzy-audio-core" > "$root/runtime-check.log" 2>&1 || { tail -n 25 "$root/runtime-check.log"; exit 1; }
if grep -q 'not found' "$root/runtime-check.log"; then tail -n 25 "$root/runtime-check.log"; echo 'BŁĄD: Brakuje zależności systemowych JACK lub glibc.'; exit 1; fi
"$root/bin/jerzy-audio-core" --list-lv2 > "$root/lv2-discovery.json" || exit 1
python3 -c 'import json; p=json.load(open("lv2-discovery.json")); print("Wykryto wtyczek LV2:", len(p["plugins"]))'
base="$HOME/.local/share/jerzy-audio-platform"
mkdir -p "$base/releases" "$base/presets" "$base/irs" "$base/modules" "$base/lv2"
# Do not overwrite a prior release or an interrupted installation.
version=$(python3 -c 'import json;print(json.load(open("BUILD-METADATA.json"))["version"])')
release="$base/releases/$version-$(date +%Y%m%d-%H%M%S)-$$"
mkdir "$release"
cp -R "$root"/. "$release"/
for module in "$release"/modules/*; do
 [ -d "$module" ] || continue
 name=$(basename "$module")
 # Preserve existing user-installed versions.
 [ -e "$base/modules/$name" ] || cp -R "$module" "$base/modules/$name"
done
printf '%s\n' "$release" > "$base/staged.tmp"
mv "$base/staged.tmp" "$base/staged"
if command -v loginctl >/dev/null; then
 echo 'Aby panel działał po wylogowaniu SSH, aktywacja sprawdzi trwałość usług użytkownika.'
fi
echo "STAGING ZAKOŃCZONY. Pliki: $release"
echo 'Dotychczasowe usługi, JACK i sieć nadal działają bez zmian.'
echo "Aktywacja: python3 '$release/deploy/raspberry-pi/control.py' activate"
