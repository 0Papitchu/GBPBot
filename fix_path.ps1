$currentPath = $env:Path -split ';' | Where-Object { $_ -ne '' } | Select-Object -Unique
$cleanPath = $currentPath | ForEach-Object { 
    $_ -replace '"', '' -replace '‪', '' 
} | Where-Object { 
    $_ -ne '' -and (Test-Path $_)
} | Select-Object -Unique

$newPath = $cleanPath -join ';'
[Environment]::SetEnvironmentVariable('Path', $newPath, 'User')
Write-Host "PATH has been cleaned and updated." 