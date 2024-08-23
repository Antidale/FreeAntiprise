if ((Test-Path env:VIRTUAL_ENV) -eq $false) { .\ENV\Scripts\Activate.ps1 }
python .\fetools\tool_site.py .\ff4.rom.smc