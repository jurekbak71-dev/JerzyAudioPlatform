$ErrorActionPreference = 'Stop'
try {
    $hostPi = Read-Host 'Aktualne IP Pi [ENTER = bassambient.local]'
    if (-not $hostPi) { $hostPi = 'bassambient.local' }
    if ($hostPi -notmatch '^[a-zA-Z0-9][a-zA-Z0-9.-]{0,252}$') { throw 'Nieprawidlowy adres.' }
    Write-Host 'Nowa platforma stanie sie domyslnym hostem po restarcie. Poprzednie ustawienia startu zostana zachowane.'
    if ((Read-Host 'Po sprawdzeniu dzwieku wpisz TAK') -cne 'TAK') { exit 0 }
    $command = 'release=$(cat "$HOME/.local/share/jerzy-audio-platform/staged") && sudo -v && python3 "$release/deploy/raspberry-pi/control.py" autostart'
    & ssh.exe -t "jerzy@$hostPi" $command
    if ($LASTEXITCODE -ne 0) { throw 'Nie potwierdzono autostartu. Zachowaj komunikat powyzej.' }
    exit 0
} catch { Write-Host ('BLAD: '+$_.Exception.Message) -ForegroundColor Red; exit 1 }
