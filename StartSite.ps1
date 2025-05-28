if ((Test-Path env:VIRTUAL_ENV) -eq $false) { 
    if ((Test-Path ./ENV/Scripts) -eq $false) {
        pwsh ./ENV/bin/Activate.ps1 && python -m FreeEnt ./ff4.rom.smc server --local
    }

    ./ENV/Scripts/Activate.ps1 
}
