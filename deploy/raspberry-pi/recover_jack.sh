#!/usr/bin/env bash
# Explicit recovery after an ALSA device disconnect. Preserve JACK configuration.
set -u
report="$HOME/JERZY-NAPRAWA-$(date +%Y%m%d-%H%M%S).txt"
exec > >(tee "$report") 2>&1
if [[ ! -e /proc/asound/Core ]]; then
  echo 'BRAK HEADRUSH CORE. Włącz urządzenie i podłącz USB, potem ponów ten blok.'
  cat /proc/asound/cards 2>/dev/null || true
  echo "Nic nie przełączono. Raport: $report"
  exit 3
fi
sudo -v || exit 1
mapfile -t previous < <(systemctl list-units --type=service --state=active,activating,reloading --plain --no-legend 'jerzy-multifx*.service' | awk '{print $1}')
restore() {
  if ((${#previous[@]})); then
    sudo -n systemctl start --no-block "${previous[@]}" || true
  fi
}
trap restore EXIT
trap 'exit 130' INT
trap 'exit 143' TERM HUP
echo 'Restart JACK z dotychczasową konfiguracją...'
sudo systemctl restart jerzy-jack.service || exit 1
ready=0
for ((i=0;i<15;i++)); do
  if timeout 2 jack_lsp > "$report.ports" 2>&1 && grep -q '^system:playback_' "$report.ports"; then
    ready=1
    break
  fi
  sleep 1
done
if (( ! ready )); then
  cat "$report.ports"
  journalctl -u jerzy-jack.service -b --no-pager -n 30
  echo "JACK nadal niedostępny. Nie uruchomiono nowej platformy. Raport: $report"
  exit 1
fi
cat "$report.ports"
if ((${#previous[@]})); then
  timeout 50 sudo -n systemctl start "${previous[@]}" || exit 1
fi
# Recovery of previous services is complete; successful platform activation must
# not be followed by restarting the previous audio clients.
trap - EXIT
staged="$HOME/.local/share/jerzy-audio-platform/staged"
if [[ ! -f "$staged" ]]; then
  echo "JACK działa. Brak przygotowanej paczki platformy. Raport: $report"
  exit 1
fi
release=$(cat "$staged")
if [[ "$release" != "$HOME/.local/share/jerzy-audio-platform/releases/"* || ! -f "$release/deploy/raspberry-pi/control.py" ]]; then
  echo 'Nieprawidłowa ścieżka przygotowanej paczki.'
  exit 1
fi
sudo -v || exit 1
python3 "$release/deploy/raspberry-pi/control.py" activate
result=$?
echo "Raport: $report"
if ((result==0)); then echo 'Panel: http://10.42.0.1:8093/'; fi
exit "$result"
