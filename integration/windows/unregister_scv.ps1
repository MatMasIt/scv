# Remove only SCV-owned current-user associations; does not delete user content.
$base = 'HKCU:\Software\Classes'
Remove-Item -Path "$base\.scv" -Force -ErrorAction SilentlyContinue
Remove-Item -Path "$base\SCV.Lecture" -Recurse -Force -ErrorAction SilentlyContinue
Write-Host 'SCV association removed. Windows may cache previous defaults.'
