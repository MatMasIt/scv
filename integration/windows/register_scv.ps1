# User-level file association; edit $PlayerCommand to your packaged player EXE path.
param([Parameter(Mandatory=$true)][string]$PlayerCommand)
$base = 'HKCU:\Software\Classes'
New-Item -Path "$base\.scv" -Force | Out-Null
Set-Item -Path "$base\.scv" -Value 'SCV.Lecture'
New-Item -Path "$base\SCV.Lecture" -Force | Out-Null
Set-Item -Path "$base\SCV.Lecture" -Value 'Slide Compressed Video lecture'
New-Item -Path "$base\SCV.Lecture\shell\open\command" -Force | Out-Null
Set-Item -Path "$base\SCV.Lecture\shell\open\command" -Value ('"' + $PlayerCommand + '" "%1"')
Write-Host 'Association registered. Windows may still ask you to choose the default app in Settings.'
