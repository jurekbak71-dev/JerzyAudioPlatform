$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
try {
    $hostPi = Read-Host 'Adres Pi w aktualnej sieci [ENTER = bassambient.local]'
    if (-not $hostPi) { $hostPi = 'bassambient.local' }
    if ($hostPi -notmatch '^[a-zA-Z0-9][a-zA-Z0-9.-]{0,252}$') { throw 'Nieprawidlowy adres.' }
    $catalog = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'MODULE-CATALOG.json') -Raw -Encoding UTF8 | ConvertFrom-Json
    Add-Type -AssemblyName System.Windows.Forms
    $dialog = New-Object System.Windows.Forms.OpenFileDialog
    $dialog.Filter = 'Moduly Jerzy (*.jamod)|*.jamod'
    $dialog.Multiselect = $true
    $dialog.Title = 'Wybierz jeden lub kilka oryginalnych modulow'
    if ($dialog.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK) { exit 0 }
    $selected = @()
    foreach ($file in $dialog.FileNames) {
        $name = [System.IO.Path]::GetFileName($file)
        $entry = $catalog.PSObject.Properties[$name]
        if (-not $entry -or $entry.Value.sha256 -notmatch '^[a-f0-9]{64}$') { throw "Brak $name w zaufanym katalogu tej wersji. Pobierz aktualny instalator modulow." }
        $actual = (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($actual -ne $entry.Value.sha256) { throw "Niezgodna SHA256 paczki $name." }
        $selected += [pscustomobject]@{ File=$file; Name=$name; Sum=$actual }
    }
    $remote = '/tmp/jerzy-moduly-' + [guid]::NewGuid().ToString('N')
    $target = "jerzy@$hostPi"
    & ssh.exe $target "mkdir -m 700 '$remote'"
    if ($LASTEXITCODE -ne 0) { throw 'Nie utworzono katalogu przesylania.' }
    $arguments = @((Join-Path $PSScriptRoot 'install_module.py')) + @($selected | ForEach-Object { $_.File }) + @("${target}:$remote/")
    & scp.exe @arguments
    if ($LASTEXITCODE -ne 0) { throw 'Nie przeslano paczek.' }
    foreach ($entry in $selected) {
        $command = "python3 '$remote/install_module.py' '$remote/$($entry.Name)' '$($entry.Sum)'"
        & ssh.exe $target $command
        if ($LASTEXITCODE -ne 0) { throw "Nie zainstalowano $($entry.Name). Zachowaj komunikat powyzej." }
    }
    Write-Host 'Moduly sa w Bibliotece. Wybierz tor w Lancuchu i dodaj wybrany modul.' -ForegroundColor Green
    Start-Process "http://${hostPi}:8093/"
    exit 0
} catch { Write-Host ('BLAD: ' + $_.Exception.Message) -ForegroundColor Red; exit 1 }
