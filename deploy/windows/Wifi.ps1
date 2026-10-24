$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
try {
    Write-Host 'Polaczenie Raspberry Pi z domowym Wi-Fi. Hotspot zostanie zachowany.' -ForegroundColor Green
    $old = Read-Host 'Aktualny adres Pi [ENTER = 10.42.0.1]'
    if (-not $old) { $old = '10.42.0.1' }
    if ($old -notmatch '^[a-zA-Z0-9][a-zA-Z0-9.-]{0,252}$') { throw 'Nieprawidlowy adres.' }
    $script = Join-Path $PSScriptRoot 'wifi_home.py'
    $sum = (Get-FileHash -LiteralPath $script -Algorithm SHA256).Hash.ToLowerInvariant()
    $remote = '/tmp/jerzy-wifi-' + [guid]::NewGuid().ToString('N') + '.py'
    & scp.exe $script "jerzy@${old}:$remote"
    if ($LASTEXITCODE -ne 0) { throw 'Nie przeslano narzedzia Wi-Fi.' }
    Write-Host 'Na Pi podaj SSID i haslo domowego Wi-Fi. Haslo nie trafi do raportu ani polecen.'
    & ssh.exe -t "jerzy@$old" "echo '$sum  $remote' | sha256sum -c - && sudo python3 '$remote' prepare"
    if ($LASTEXITCODE -ne 0) { throw 'Nie rozpoczeto zmiany Wi-Fi.' }
    Write-Host 'TERAZ POLACZ WINDOWS Z DOMOWYM WI-FI. Masz 5 minut. Nie zamykaj tego okna.' -ForegroundColor Yellow
    Read-Host 'Po polaczeniu Windows z domowym Wi-Fi nacisnij ENTER' | Out-Null
    $new = Read-Host 'Nowe IP Pi z routera [ENTER = bassambient.local]'
    if (-not $new) { $new = 'bassambient.local' }
    if ($new -notmatch '^[a-zA-Z0-9][a-zA-Z0-9.-]{0,252}$') { throw 'Nieprawidlowy adres.' }
    # Reuse the known hotspot host key, not a new unverified LAN identity.
    & ssh.exe -t -o "HostKeyAlias=$old" -o 'ConnectTimeout=8' "jerzy@$new" "sudo python3 '$remote' confirm"
    if ($LASTEXITCODE -ne 0) { throw 'Nie potwierdzono polaczenia. Po uplywie 5 minut narzedzie podejmie przywrocenie poprzedniego profilu. Nie kasuj hotspotu.' }
    Write-Host "Panel w domowej sieci: http://${new}:8093/" -ForegroundColor Green
    Start-Process "http://${new}:8093/"
    exit 0
} catch { Write-Host ('BLAD: ' + $_.Exception.Message) -ForegroundColor Red; exit 1 }
