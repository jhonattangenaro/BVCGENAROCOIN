# 1. Configuración de carpetas y fechas
$CarpetaDestino = ".\datos_dat"
if (!(Test-Path $CarpetaDestino)) { New-Item -ItemType Directory -Path $CarpetaDestino }

$FechaInicio = Get-Date -Year 2024 -Month 01 -Day 01  # Cambia esto a la fecha que desees
$FechaFin = Get-Date
$BaseUrl = "https://www.bolsadecaracas.com/descargar-diario-bolsa/?type=dat&fecha="

# 2. Bucle de descarga
while ($FechaInicio -le $FechaFin) {
    # Solo intentar si es lunes a viernes (1 al 5)
    if ($FechaInicio.DayOfWeek -ne "Saturday" -and $FechaInicio.DayOfWeek -ne "Sunday") {
        
        $FechaString = $FechaInicio.ToString("yyyyMMdd")
        $UrlDescarga = $BaseUrl + $FechaString
        $NombreArchivo = "diario_bolsa_$FechaString.dat"
        $RutaCompleta = Join-Path $CarpetaDestino $NombreArchivo

        Write-Host "Intentando descargar: $FechaString..." -ForegroundColor Cyan

        try {
            # Intentamos descargar el archivo
            Invoke-WebRequest -Uri $UrlDescarga -OutFile $RutaCompleta -ErrorAction Stop
            
            # Verificar si el archivo está vacío o es un HTML de error (la web a veces devuelve 200 OK pero con error)
            $FileInfo = Get-Item $RutaCompleta
            if ($FileInfo.Length -lt 500) {
                Remove-Item $RutaCompleta
                Write-Host "No hay datos para la fecha $FechaString (Feriado o no disponible)." -ForegroundColor Yellow
            } else {
                Write-Host "✅ ¡Guardado!: $NombreArchivo" -ForegroundColor Green
            }
        }
        catch {
            Write-Host "❌ Error en fecha $FechaString" -ForegroundColor Red
        }
    }
    
    # Avanzar un día
    $FechaInicio = $FechaInicio.AddDays(1)
}

Write-Host "`n--- Proceso Finalizado ---" -ForegroundColor White -BackgroundColor DarkGreen