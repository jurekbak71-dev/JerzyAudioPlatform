$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
try {
    Write-Host 'Naprawa polaczenia JACK i ponowna aktywacja platformy.' -ForegroundColor Green
    Write-Host 'Wlacz HeadRush Core i podlacz go przez USB. Nastapi restart audio, bez zmiany sieci.'
    $adres = Read-Host 'IP Raspberry Pi [ENTER = 10.42.0.1]'
    if (-not $adres) { $adres = '10.42.0.1' }
    if ($adres -notmatch '^[a-zA-Z0-9][a-zA-Z0-9.-]{0,252}$') { throw 'Nieprawidlowy adres.' }
    foreach ($program in @('ssh.exe','scp.exe')) {
        if (-not (Get-Command $program -ErrorAction SilentlyContinue)) { throw "Brak $program. Wlacz Klient OpenSSH w Windows." }
    }
    $script = Join-Path $PSScriptRoot 'recover_jack.sh'
    $sum = (Get-FileHash -LiteralPath $script -Algorithm SHA256).Hash.ToLowerInvariant()
    $remote = '/tmp/jerzy-recover-' + [guid]::NewGuid().ToString('N') + '.sh'
    $target = "jerzy@$adres"
    & scp.exe $script "${target}:$remote"
    if ($LASTEXITCODE -ne 0) { throw 'Nie udalo sie przeslac poprawki.' }
    $command = "echo '$sum  $remote' | sha256sum -c - && bash '$remote'"
    & ssh.exe -t $target $command
    if ($LASTEXITCODE -ne 0) { throw 'Naprawa lub aktywacja nie zakonczyla sie powodzeniem. Zachowaj widoczny raport.' }
    Write-Host "Aktywacja potwierdzona. Panel: http://${adres}:8093/" -ForegroundColor Green
    Start-Process "http://${adres}:8093/"
    exit 0
} catch {
    Write-Host ('BLAD: ' + $_.Exception.Message) -ForegroundColor Red
    exit 1
}
