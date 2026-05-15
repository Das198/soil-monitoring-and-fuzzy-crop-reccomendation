@echo off
:: Upload file ke VPS via IAP tunnel
:: Usage: upload_vps.bat <file_lokal> <path_tujuan_di_vps>
:: Contoh: upload_vps.bat flows.json /home/dteoproyektanah/.node-red/flows.json

set INSTANCE=server-monitoring
set USER=dteoproyektanah

if "%~1"=="" (
    echo Usage: upload_vps.bat ^<file_lokal^> ^<path_tujuan^>
    exit /b 1
)

echo Mengupload %~1 ke VPS...
gcloud compute scp --tunnel-through-iap "%~1" %USER%@%INSTANCE%:%~2
echo Selesai.
