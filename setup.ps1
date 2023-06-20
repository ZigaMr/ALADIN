# Check if Python is installed
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Output "Python not found. Installing Python..."
    choco install python -y
}

# Check if Poetry is installed
if (-not (Get-Command poetry -ErrorAction SilentlyContinue)) {
    Write-Output "Poetry not found. Installing Poetry..."
    choco install poetry -y
}

# Check if MySQL is installed
if (-not (Get-Command mysql -ErrorAction SilentlyContinue)) {
    Write-Output "MySQL not found. Installing MySQL..."
    choco install mysql -y
}

# Initialize Poetry environment from requirements.txt
Write-Output "Initializing Poetry environment..."
poetry install

# Create a new MySQL database
Write-Output "Creating a new MySQL database..."
mysql -u root -p -e "CREATE DATABASE Aladin;"

# Schedule main.py to run every hour
Write-Output "Scheduling main.py to run every hour..."
$taskName = "WeatherData"
$action = New-ScheduledTaskAction -Execute "python" -Argument "main.py"
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Hours 1) -RepetitionDuration ([System.TimeSpan]::MaxValue)
Register-ScheduledTask -TaskName $taskName -Trigger $trigger -Action $action

Write-Output "Setup completed successfully."
