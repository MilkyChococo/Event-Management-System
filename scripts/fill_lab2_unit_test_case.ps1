param(
  [string]$TemplatePath = 'E:\Downloads\Lab2-WritingUnitTestCase (2)\Lab2-WritingUnitTestCase\Template_Unit Test Case.xls',
  [string]$OutputPath = 'E:\se113.q21\docs\lab2\EventHubVerify_Lab2_Unit_Test_Case.xls'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if (-not (Test-Path $TemplatePath)) {
  throw "Template not found: $TemplatePath"
}

$null = New-Item -ItemType Directory -Force (Split-Path -Parent $OutputPath)
Copy-Item $TemplatePath $OutputPath -Force

$excel = New-Object -ComObject Excel.Application
$excel.Visible = $false
$excel.DisplayAlerts = $false
$workbook = $excel.Workbooks.Open($OutputPath)

function Set-Cell($ws, [int]$row, [int]$col, $value) {
  $ws.Cells.Item($row, $col).Value = [string]$value
}

function Set-CaseHeaders($ws, [string[]]$headers) {
  for ($i = 0; $i -lt $headers.Length; $i++) {
    Set-Cell $ws 9 (6 + $i) $headers[$i]
  }
}

function Mark-O($ws, [int]$row, [int[]]$caseColumns) {
  foreach ($col in $caseColumns) {
    Set-Cell $ws $row $col 'O'
  }
}

function Fill-ResultRows($ws, [string[]]$types, [string[]]$statuses, [string]$dateText) {
  for ($i = 0; $i -lt $types.Length; $i++) {
    $col = 6 + $i
    Set-Cell $ws 45 $col $types[$i]
    Set-Cell $ws 46 $col $statuses[$i]
    Set-Cell $ws 47 $col $dateText
  }
}

function Prepare-FunctionSheet($ws, [string]$functionCode, [string]$functionName, [int]$loc, [string]$requirement, [int]$passed, [int]$failed, [int]$untested, [int]$normalCount, [int]$abnormalCount, [int]$boundaryCount, [int]$totalCount) {
  for ($row = 9; $row -le 48; $row++) {
    for ($col = 6; $col -le 20; $col++) {
      Set-Cell $ws $row $col ''
    }
  }
  for ($row = 11; $row -le 44; $row++) {
    Set-Cell $ws $row 2 ''
    Set-Cell $ws $row 4 ''
  }
  Set-Cell $ws 2 3 $functionCode
  Set-Cell $ws 2 12 $functionName
  Set-Cell $ws 3 3 'Team EventHub Verify'
  Set-Cell $ws 3 12 'Team EventHub Verify'
  Set-Cell $ws 4 3 $loc
  Set-Cell $ws 4 12 0
  Set-Cell $ws 5 3 $requirement
  Set-Cell $ws 7 1 $passed
  Set-Cell $ws 7 3 $failed
  Set-Cell $ws 7 6 $untested
  Set-Cell $ws 7 12 $normalCount
  Set-Cell $ws 7 13 $abnormalCount
  Set-Cell $ws 7 14 $boundaryCount
  Set-Cell $ws 7 15 $totalCount
}

# Cover
$cover = $workbook.Worksheets.Item('Cover')
Set-Cell $cover 4 2 'Event Registration System'
Set-Cell $cover 5 2 'ERS-SE113'
Set-Cell $cover 6 2 'ERS-SE113_UTC_v1.0'
Set-Cell $cover 4 6 'Team EventHub Verify'
Set-Cell $cover 5 6 'Pending lecturer review'
Set-Cell $cover 6 6 '03/31/2026'
Set-Cell $cover 7 6 '1.0'
Set-Cell $cover 12 1 '03/31/2026'
Set-Cell $cover 12 2 '1.0'
Set-Cell $cover 12 3 'Initial release'
Set-Cell $cover 12 4 'A'
Set-Cell $cover 12 5 'Filled Lab 2 unit test cases for core service functions of EventHub Verify.'
Set-Cell $cover 12 6 'README.md, tests/test_services.py'

# Function list
$functionList = $workbook.Worksheets.Item('FunctionList')
Set-Cell $functionList 4 5 'Event Registration System'
Set-Cell $functionList 5 5 'ERS-SE113'
Set-Cell $functionList 7 5 "1. FastAPI application`n2. MongoDB (or mongomock in tests)`n3. Python runtime`n4. TestClient / unittest environment"
Set-Cell $functionList 11 1 1
Set-Cell $functionList 11 2 'FR-Auth'
Set-Cell $functionList 11 3 'EventRegistrationService'
Set-Cell $functionList 11 4 'authenticate'
Set-Cell $functionList 11 5 'AUTHENTICATE'
Set-Cell $functionList 11 6 'Function1'
Set-Cell $functionList 11 7 'Validate account existence, credentials, and login cleanup behavior.'
Set-Cell $functionList 11 8 'Seeded account data is available in MongoDB/mongomock.'

Set-Cell $functionList 12 1 2
Set-Cell $functionList 12 2 'FR-Reservation'
Set-Cell $functionList 12 3 'EventRegistrationService'
Set-Cell $functionList 12 4 'register_for_event'
Set-Cell $functionList 12 5 'REGISTER_FOR_EVENT'
Set-Cell $functionList 12 6 'Function2'
Set-Cell $functionList 12 7 'Reserve tickets with quantity, balance, duplicate, and capacity validation.'
Set-Cell $functionList 12 8 'Approved event and user account are prepared before execution.'

Set-Cell $functionList 13 1 3
Set-Cell $functionList 13 2 'FR-Moderation'
Set-Cell $functionList 13 3 'EventRegistrationService'
Set-Cell $functionList 13 4 'update_owned_event'
Set-Cell $functionList 13 5 'UPDATE_OWNED_EVENT'
Set-Cell $functionList 13 6 'Function3'
Set-Cell $functionList 13 7 'Update user-owned event requests and return them to pending review.'
Set-Cell $functionList 13 8 'A user-owned event request already exists for update scenarios.'

# Test report
$testReport = $workbook.Worksheets.Item('Test Report')
Set-Cell $testReport 4 2 'Event Registration System'
Set-Cell $testReport 5 2 'ERS-SE113'
Set-Cell $testReport 6 2 'ERS-SE113_TestReport_v1.0'
Set-Cell $testReport 4 5 'Team EventHub Verify'
Set-Cell $testReport 5 5 'Pending lecturer review'
Set-Cell $testReport 6 6 '03/31/2026'
Set-Cell $testReport 7 2 'Core service functions covered: authentication, reservation, and event request update.'

Set-Cell $testReport 12 2 'AUTHENTICATE'
Set-Cell $testReport 12 3 5
Set-Cell $testReport 12 4 0
Set-Cell $testReport 12 5 0
Set-Cell $testReport 12 6 3
Set-Cell $testReport 12 7 2
Set-Cell $testReport 12 8 0
Set-Cell $testReport 12 9 5

Set-Cell $testReport 13 2 'REGISTER_FOR_EVENT'
Set-Cell $testReport 13 3 6
Set-Cell $testReport 13 4 0
Set-Cell $testReport 13 5 0
Set-Cell $testReport 13 6 1
Set-Cell $testReport 13 7 3
Set-Cell $testReport 13 8 2
Set-Cell $testReport 13 9 6

Set-Cell $testReport 14 2 'UPDATE_OWNED_EVENT'
Set-Cell $testReport 14 3 4
Set-Cell $testReport 14 4 0
Set-Cell $testReport 14 5 0
Set-Cell $testReport 14 6 2
Set-Cell $testReport 14 7 2
Set-Cell $testReport 14 8 0
Set-Cell $testReport 14 9 4

# Function1 - AUTHENTICATE
$f1 = $workbook.Worksheets.Item('Function1')
Prepare-FunctionSheet $f1 'AUTHENTICATE' 'authenticate(email, password)' 18 'Verify account lookup, password validation, email normalization, and old-notification cleanup during login.' 5 0 0 3 2 0 5
Set-CaseHeaders $f1 @('UTC-AUTH-01','UTC-AUTH-02','UTC-AUTH-03','UTC-AUTH-04','UTC-AUTH-05')
Set-Cell $f1 11 2 'Seeded student account exists in MongoDB/mongomock'
Set-Cell $f1 14 2 'User record exists'
Set-Cell $f1 15 4 'No'
Set-Cell $f1 16 4 'Yes'
Set-Cell $f1 19 2 'Password matches stored hash'
Set-Cell $f1 20 4 'No'
Set-Cell $f1 21 4 'Yes'
Set-Cell $f1 24 2 'Expired notifications older than 5 days exist'
Set-Cell $f1 25 4 'No'
Set-Cell $f1 26 4 'Yes'
Set-Cell $f1 29 2 'Email requires trim/lowercase normalization'
Set-Cell $f1 30 4 'No'
Set-Cell $f1 31 4 'Yes'
Mark-O $f1 16 @(6,7,9,10)
Mark-O $f1 15 @(8)
Mark-O $f1 21 @(6,7,10)
Mark-O $f1 20 @(9)
Mark-O $f1 25 @(6,9,10)
Mark-O $f1 26 @(7)
Mark-O $f1 30 @(6,7,8,9)
Mark-O $f1 31 @(10)
Set-Cell $f1 33 1 'Confirm'
Set-Cell $f1 34 2 'Notification cleanup'
Set-Cell $f1 35 4 'Expired notifications are purged'
Mark-O $f1 35 @(7)
Set-Cell $f1 37 2 'Return'
Set-Cell $f1 38 4 'Serialized user object'
Mark-O $f1 38 @(6,7,10)
Set-Cell $f1 40 2 'Exception'
Set-Cell $f1 41 4 'ACCOUNT_NOT_FOUND'
Set-Cell $f1 42 4 'INVALID_CREDENTIALS'
Mark-O $f1 41 @(8)
Mark-O $f1 42 @(9)
Fill-ResultRows $f1 @('N','N','A','A','N') @('Passed','Passed','Passed','Passed','Passed') '03/31/2026'

# Function2 - REGISTER_FOR_EVENT
$f2 = $workbook.Worksheets.Item('Function2')
Prepare-FunctionSheet $f2 'REGISTER_FOR_EVENT' 'register_for_event(user_id, event_id, payload)' 76 'Verify successful reservation, boundary quantities, duplicate protection, insufficient balance handling, and seat-capacity enforcement.' 6 0 0 1 3 2 6
Set-CaseHeaders $f2 @('UTC-RES-01','UTC-RES-02','UTC-RES-03','UTC-RES-04','UTC-RES-05','UTC-RES-06')
Set-Cell $f2 11 2 'Approved event and test user are seeded before execution'
Set-Cell $f2 14 2 'Existing active registration'
Set-Cell $f2 15 4 'No'
Set-Cell $f2 16 4 'Yes'
Set-Cell $f2 19 2 'Requested quantity'
Set-Cell $f2 20 4 '1'
Set-Cell $f2 21 4 '5'
Set-Cell $f2 22 4 '6'
Set-Cell $f2 25 2 'Seats are enough'
Set-Cell $f2 26 4 'No'
Set-Cell $f2 27 4 'Yes'
Set-Cell $f2 30 2 'Balance is enough'
Set-Cell $f2 31 4 'No'
Set-Cell $f2 32 4 'Yes'
Mark-O $f2 15 @(6,7,8,10,11)
Mark-O $f2 16 @(9)
Mark-O $f2 20 @(6,9,10,11)
Mark-O $f2 21 @(7)
Mark-O $f2 22 @(8)
Mark-O $f2 26 @(11)
Mark-O $f2 27 @(6,7,8,9,10)
Mark-O $f2 31 @(10)
Mark-O $f2 32 @(6,7,8,9,11)
Set-Cell $f2 33 1 'Return'
Set-Cell $f2 34 2 'Reservation result'
Set-Cell $f2 35 4 'Registration object is returned'
Mark-O $f2 35 @(6,7)
Set-Cell $f2 37 2 'Confirm'
Set-Cell $f2 38 4 'Seats and balance are updated'
Mark-O $f2 38 @(6,7)
Set-Cell $f2 40 2 'Exception'
Set-Cell $f2 41 4 'TICKET_LIMIT_EXCEEDED'
Set-Cell $f2 42 4 'ALREADY_REGISTERED'
Set-Cell $f2 43 4 'INSUFFICIENT_FUNDS'
Set-Cell $f2 44 4 'EVENT_FULL'
Mark-O $f2 41 @(8)
Mark-O $f2 42 @(9)
Mark-O $f2 43 @(10)
Mark-O $f2 44 @(11)
Fill-ResultRows $f2 @('N','B','B','A','A','A') @('Passed','Passed','Passed','Passed','Passed','Passed') '03/31/2026'

# Function3 - UPDATE_OWNED_EVENT
$f3 = $workbook.Worksheets.Item('Function3')
Prepare-FunctionSheet $f3 'UPDATE_OWNED_EVENT' 'update_owned_event(user_id, event_id, payload)' 58 'Verify owner validation, request update, review status reset, and notification side effects after event-request updates.' 4 0 0 2 2 0 4
Set-CaseHeaders $f3 @('UTC-UPD-01','UTC-UPD-02','UTC-UPD-03','UTC-UPD-04')
Set-Cell $f3 11 2 'Student-owned event request exists for update scenarios'
Set-Cell $f3 14 2 'User account exists'
Set-Cell $f3 15 4 'No'
Set-Cell $f3 16 4 'Yes'
Set-Cell $f3 19 2 'Owned event exists for the user'
Set-Cell $f3 20 4 'No'
Set-Cell $f3 21 4 'Yes'
Set-Cell $f3 24 2 'Coordinates are provided'
Set-Cell $f3 25 4 'No'
Set-Cell $f3 26 4 'Yes'
Set-Cell $f3 29 2 'Gallery images are provided'
Set-Cell $f3 30 4 'No'
Set-Cell $f3 31 4 'Yes'
Mark-O $f3 16 @(6,8,9)
Mark-O $f3 15 @(7)
Mark-O $f3 20 @(8)
Mark-O $f3 21 @(6,9)
Mark-O $f3 25 @(6,7,8)
Mark-O $f3 26 @(9)
Mark-O $f3 30 @(6,7,8)
Mark-O $f3 31 @(9)
Set-Cell $f3 33 1 'Return'
Set-Cell $f3 34 2 'Updated event request'
Set-Cell $f3 35 4 'Updated event payload is returned'
Mark-O $f3 35 @(6,9)
Set-Cell $f3 37 2 'Confirm'
Set-Cell $f3 38 4 'Approval status is reset to pending review'
Set-Cell $f3 39 4 'Admin review notification is created'
Mark-O $f3 38 @(6,9)
Mark-O $f3 39 @(6,9)
Set-Cell $f3 41 2 'Exception'
Set-Cell $f3 42 4 'ACCOUNT_NOT_FOUND'
Set-Cell $f3 43 4 'EVENT_NOT_FOUND'
Mark-O $f3 42 @(7)
Mark-O $f3 43 @(8)
Fill-ResultRows $f3 @('N','A','A','N') @('Passed','Passed','Passed','Passed') '03/31/2026'

$workbook.Save()
$workbook.Close($true)
$excel.Quit()
[System.Runtime.Interopservices.Marshal]::ReleaseComObject($f1) | Out-Null
[System.Runtime.Interopservices.Marshal]::ReleaseComObject($f2) | Out-Null
[System.Runtime.Interopservices.Marshal]::ReleaseComObject($f3) | Out-Null
[System.Runtime.Interopservices.Marshal]::ReleaseComObject($testReport) | Out-Null
[System.Runtime.Interopservices.Marshal]::ReleaseComObject($functionList) | Out-Null
[System.Runtime.Interopservices.Marshal]::ReleaseComObject($cover) | Out-Null
[System.Runtime.Interopservices.Marshal]::ReleaseComObject($workbook) | Out-Null
[System.Runtime.Interopservices.Marshal]::ReleaseComObject($excel) | Out-Null
[gc]::Collect()
[gc]::WaitForPendingFinalizers()

Write-Output "Generated: $OutputPath"

