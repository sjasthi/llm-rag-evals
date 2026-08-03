[CmdletBinding()]
param(
    [ValidateRange(1, 65535)]
    [int]$Port = 3306,

    [ValidateRange(1, 120)]
    [int]$StartupTimeoutSeconds = 20,

    [string]$RuntimeRoot = (Join-Path $env:LOCALAPPDATA 'LLMRAGEvals'),

    [string]$MySqlServer = (Join-Path $env:ProgramFiles 'MySQL\MySQL Server 8.4\bin\mysqld.exe')
)

$ErrorActionPreference = 'Stop'

function Get-LocalListener {
    Get-NetTCPConnection `
        -State Listen `
        -LocalAddress '127.0.0.1' `
        -LocalPort $Port `
        -ErrorAction SilentlyContinue |
        Select-Object -First 1
}

$listener = Get-LocalListener
if ($listener) {
    $listenerProcess = Get-Process -Id $listener.OwningProcess -ErrorAction SilentlyContinue
    if ($listenerProcess -and $listenerProcess.ProcessName -eq 'mysqld') {
        Write-Output "Local MySQL is already ready on 127.0.0.1:$Port (PID $($listener.OwningProcess))."
        exit 0
    }
    throw "Port $Port is already in use by a process other than MySQL."
}

if (-not (Test-Path -LiteralPath $MySqlServer -PathType Leaf)) {
    throw "MySQL Server was not found at '$MySqlServer'. Install MySQL 8.4 or pass -MySqlServer with the mysqld.exe path."
}

$dataDirectory = Join-Path $RuntimeRoot 'mysql-data'
$systemDatabase = Join-Path $dataDirectory 'mysql'
if (-not (Test-Path -LiteralPath $systemDatabase -PathType Container)) {
    throw "No initialized MySQL data directory was found at '$dataDirectory'. This launcher will never initialize or replace a database."
}

if (-not (Test-Path -LiteralPath $RuntimeRoot -PathType Container)) {
    throw "The local runtime directory '$RuntimeRoot' does not exist."
}

$pidFile = Join-Path $RuntimeRoot 'mysql.pid'
$errorLog = Join-Path $RuntimeRoot 'mysql-error.log'
$arguments = @(
    "--datadir=$dataDirectory"
    "--port=$Port"
    '--bind-address=127.0.0.1'
    '--mysqlx=OFF'
    "--pid-file=$pidFile"
    "--log-error=$errorLog"
    '--secure-file-priv=NULL'
)

$process = Start-Process `
    -FilePath $MySqlServer `
    -ArgumentList $arguments `
    -WindowStyle Hidden `
    -PassThru

$deadline = [DateTime]::UtcNow.AddSeconds($StartupTimeoutSeconds)
do {
    Start-Sleep -Milliseconds 250
    $listener = Get-LocalListener
    if ($listener) {
        $listenerProcess = Get-Process -Id $listener.OwningProcess -ErrorAction SilentlyContinue
        if ($listenerProcess -and $listenerProcess.ProcessName -eq 'mysqld') {
            Write-Output "Local MySQL is ready on 127.0.0.1:$Port (PID $($listener.OwningProcess))."
            exit 0
        }
        throw "Port $Port became occupied by a process other than MySQL."
    }
} while ([DateTime]::UtcNow -lt $deadline -and -not $process.HasExited)

$logHint = if (Test-Path -LiteralPath $errorLog -PathType Leaf) {
    " Review '$errorLog'."
} else {
    ''
}
throw "MySQL did not become ready within $StartupTimeoutSeconds seconds.$logHint"
