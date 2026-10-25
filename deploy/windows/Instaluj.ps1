param([string]$Adres = '', [ValidateSet('Instalacja','Diagnostyka','Przywroc','Aktywacja','Panel')][string]$Tryb = 'Instalacja')
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
function Run-External([string]$Program, [string[]]$Arguments) {
    & $Program @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Polecenie $Program zakończyło się błędem $LASTEXITCODE." }
}
try {
    Write-Host 'JERZY AUDIO PLATFORM v0.3.0 — instalator testowy' -ForegroundColor Green
    Write-Host 'Ta paczka wymaga testu na Raspberry Pi. Nie jest wydaniem potwierdzonym sprzętowo.'
    foreach ($program in @('ssh.exe','scp.exe')) {
        if (-not (Get-Command $program -ErrorAction SilentlyContinue)) { throw "Brak $program. Włącz Klient OpenSSH w opcjonalnych funkcjach Windows i uruchom ponownie instalator." }
    }
    if (-not $Adres) {
        try {
            $candidate = [System.Net.Dns]::GetHostAddresses('bassambient.local') | Where-Object { $_.AddressFamily -eq 'InterNetwork' } | Select-Object -First 1
            if ($candidate -and (Test-NetConnection -ComputerName $candidate.IPAddressToString -Port 22 -InformationLevel Quiet -WarningAction SilentlyContinue)) { $Adres = $candidate.IPAddressToString; Write-Host "Znaleziono SSH: $Adres" }
        } catch { Write-Host 'Nie udało się odnaleźć bassambient.local.' }
    }
    if (-not $Adres) { $Adres = Read-Host 'Podaj adres IP Raspberry Pi (sprawdź listę urządzeń routera)' }
    if ($Adres -notmatch '^[a-zA-Z0-9][a-zA-Z0-9.-]{0,252}$') { throw 'Nieprawidłowy adres. Wpisz IPv4 lub nazwę hosta bez spacji.' }
    $target = "jerzy@$Adres"
    if ($Tryb -eq 'Panel') {
        Start-Process "http://${Adres}:8093/"
        exit 0
    }
    if ($Tryb -eq 'Aktywacja') {
        Write-Host 'Aktywacja przelaczy tor audio. Uzywaj osobnej kopii karty.'
        $answer = Read-Host 'Wpisz TAK, aby aktywowac platforme testowa'
        if ($answer -cne 'TAK') { exit 0 }
        $command = 'release=$(cat "$HOME/.local/share/jerzy-audio-platform/staged") && sudo -v && python3 "$release/deploy/raspberry-pi/control.py" activate'
        Run-External 'ssh.exe' @('-t',$target,$command)
        Start-Process "http://${Adres}:8093/"
        exit 0
    }
    if ($Tryb -eq 'Diagnostyka' -or $Tryb -eq 'Przywroc') {
        $operation = if ($Tryb -eq 'Diagnostyka') { 'diagnostics' } else { 'rollback' }
        $command = 'release=$(cat "$HOME/.local/share/jerzy-audio-platform/staged") && python3 "$release/deploy/raspberry-pi/control.py" ' + $operation
        if ($Tryb -eq 'Przywroc') { $command = 'sudo -v && ' + $command }
        Run-External 'ssh.exe' @('-t',$target,$command)
        exit 0
    }
    $archive = Join-Path $PSScriptRoot 'JerzyAudioPlatform-v0.3.0-RPi4-arm64.tar.gz'
    $sums = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'SHA256.json') -Raw -Encoding UTF8 | ConvertFrom-Json
    $expected = $sums.'JerzyAudioPlatform-v0.3.0-RPi4-arm64.tar.gz'
    if ($expected -notmatch '^[a-f0-9]{64}$') { throw 'Brak sumy SHA256 paczki ARM64.' }
    if ((Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expected) { throw 'Paczka ARM64 jest uszkodzona. Pobierz ZIP ponownie.' }
    Write-Host 'Przy pierwszym połączeniu zweryfikuj odcisk klucza SSH Raspberry Pi. Hasło wpisuj w komunikacie OpenSSH.'
    Run-External 'ssh.exe' @($target,'uname -m; cat /etc/os-release; command -v python3; getconf GNU_LIBC_VERSION')
    $remote = & ssh.exe $target 'mktemp -d /tmp/jerzy-platform.XXXXXX'
    if ($LASTEXITCODE -ne 0 -or $remote -notmatch '^/tmp/jerzy-platform\.[a-zA-Z0-9]+$') { throw 'Nie można utworzyć katalogu staging na Pi.' }
    $remote = $remote.Trim()
    Run-External 'scp.exe' @($archive,"${target}:$remote/platform.tar.gz")
    $stage = "cd '$remote' && echo '$expected  platform.tar.gz' | sha256sum -c - && tar -xzf platform.tar.gz && sh JerzyAudioPlatform/deploy/raspberry-pi/install.sh"
    Run-External 'ssh.exe' @('-t',$target,$stage)
    Write-Host 'STAGING zakończony. Działający MultiFX nie został zatrzymany.' -ForegroundColor Green
    $answer = Read-Host 'Aktywacja przełączy tor audio. Wpisz TAK, aby uruchomić testową platformę; ENTER zachowa dotychczasowy system'
    if ($answer -ceq 'TAK') {
        $activate = 'release=$(cat "$HOME/.local/share/jerzy-audio-platform/staged") && sudo -v && python3 "$release/deploy/raspberry-pi/control.py" activate'
        Run-External 'ssh.exe' @('-t',$target,$activate)
        Write-Host "Panel: http://${Adres}:8093/" -ForegroundColor Green
        Start-Process "http://${Adres}:8093/"
        Write-Host 'Sprawdź dźwięk, wejścia, poziomy i XRUN. Autostart wymaga oddzielnego zatwierdzenia po testach sprzętowych.'
    } else { Write-Host 'Pozostawiono pliki staging bez aktywacji.' }
    exit 0
} catch {
    Write-Host ('BŁĄD INSTALACJI: ' + $_.Exception.Message) -ForegroundColor Red
    Write-Host 'Nie uznawaj tej próby za zakończoną instalację. Uruchom Diagnostyka.ps1 lub Przywroc.ps1, jeżeli nastąpiła aktywacja.'
    exit 1
}
