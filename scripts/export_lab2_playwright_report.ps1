param(
  [string]$OutputPath = 'E:\se113.q21\docs\lab2\Lab2_Playwright_Automation_Report.docx'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Add-Paragraph($selection, [string]$text) {
  $selection.TypeText($text)
  $selection.TypeParagraph()
}

function Add-Heading($selection, [string]$text, [int]$level = 1) {
  $selection.Style = "Heading $level"
  $selection.TypeText($text)
  $selection.TypeParagraph()
  $selection.Style = 'Normal'
}

function Add-Bullets($selection, [string[]]$items) {
  $selection.Range.ListFormat.ApplyBulletDefault()
  foreach ($item in $items) {
    $selection.TypeText($item)
    $selection.TypeParagraph()
  }
  $selection.Range.ListFormat.RemoveNumbers()
}

function Add-Table($document, $selection, [object[][]]$rows) {
  $rowCount = $rows.Count
  $colCount = $rows[0].Count
  $range = $selection.Range
  $table = $document.Tables.Add($range, $rowCount, $colCount)
  $table.Borders.Enable = 1
  $table.Range.Font.Name = 'Calibri'
  $table.Range.Font.Size = 10
  for ($r = 1; $r -le $rowCount; $r++) {
    for ($c = 1; $c -le $colCount; $c++) {
      $table.Cell($r, $c).Range.Text = [string]$rows[$r - 1][$c - 1]
    }
  }
  $table.Rows.Item(1).Range.Bold = 1
  $selection.SetRange($table.Range.End, $table.Range.End)
  $selection.TypeParagraph()
  return $table
}

$null = New-Item -ItemType Directory -Force -Path (Split-Path -Parent $OutputPath)
if (Test-Path $OutputPath) {
  Remove-Item $OutputPath -Force
}

$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
$document = $word.Documents.Add()
$selection = $word.Selection

Add-Heading $selection 'Lab 2 Playwright Automation Report' 1
Add-Paragraph $selection 'Project: Event Registration System (EventHub Verify)'
Add-Paragraph $selection 'Source workbook reviewed: E:\Downloads\Group11_Lab2.xlsx'
Add-Paragraph $selection 'Report date: 2026-03-31'

Add-Heading $selection '1. Review Scope' 2
Add-Bullets $selection @(
  'Reviewed all 8 function sheets and 71 detailed cases from Group11_Lab2.xlsx.',
  'Mapped each function sheet to one executable Playwright automation scenario on the current system.',
  'Used a dedicated Playwright configuration with mock MongoDB and seeded demo data for stable execution.'
)

Add-Heading $selection '2. Workbook Summary' 2
$summaryRows = @(
  @('Feature / Function Sheet', 'Detailed Cases in Lab2', 'Implemented Playwright Scenario'),
  @('User authentication', '10', 'AUTH: registration, invalid login validation, and successful login'),
  @('Event dashboard and event detail', '7', 'EVDASH: dashboard listing and event detail opening'),
  @('Ticket reservation and cancellation', '9', 'RESERVE: reserve and cancel on detail page'),
  @('Ticket quantity limit and seat capacity validation', '10', 'CAPACITY: quantity 5 accepted, quantity 6 rejected'),
  @('Billing and QR top-up', '7', 'BILLQR: generate QR, lock form, confirm payment, record transaction'),
  @('Event request submission', '10', 'REQSUB: submit request and verify notification'),
  @('Admin event approval and rejection', '10', 'ADMINAPR: approve and reject requests in manager queue'),
  @('Notification system', '8', 'NOTIFY: approval notification contains event link')
)
Add-Table $document $selection $summaryRows | Out-Null

Add-Heading $selection '3. Files Created for Automation' 2
Add-Bullets $selection @(
  'tests/e2e/lab2-review.spec.js',
  'playwright.lab2.config.js',
  'scripts/run_lab2_server.ps1',
  'playwright-report/lab2/index.html'
)

Add-Heading $selection '4. Execution Command' 2
Add-Paragraph $selection 'npx playwright test lab2-review.spec.js --config=playwright.lab2.config.js'

Add-Heading $selection '5. Execution Result' 2
Add-Bullets $selection @(
  'Result: 8 passed / 8 total tests.',
  'Execution time: 13.6 seconds.',
  'Base URL: http://127.0.0.1:10104',
  'Environment: APP_USE_MOCK_DB=true, APP_SEED_DEMO=true',
  'HTML report: E:\se113.q21\playwright-report\lab2\index.html'
)

Add-Heading $selection '6. Test Result by Function' 2
$resultRows = @(
  @('Function Code', 'Status', 'Notes'),
  @('AUTH', 'Passed', 'Covered registration, failed login validation, and successful login.'),
  @('EVDASH', 'Passed', 'Covered dashboard search/listing and event detail navigation.'),
  @('RESERVE', 'Passed', 'Covered reservation creation and cancellation flow.'),
  @('CAPACITY', 'Passed', 'Covered quantity limit boundary through Playwright browser fetch.'),
  @('BILLQR', 'Passed', 'Covered QR generation, lock state, payment confirmation, and transaction log.'),
  @('REQSUB', 'Passed', 'Covered request submission and user notification verification.'),
  @('ADMINAPR', 'Passed', 'Covered admin approval and rejection actions in manager queue.'),
  @('NOTIFY', 'Passed', 'Covered approval notification and event detail link.' )
)
Add-Table $document $selection $resultRows | Out-Null

Add-Heading $selection '7. Review Notes' 2
Add-Bullets $selection @(
  'This Playwright suite covers one representative automation path for each function sheet in Lab2.',
  'Several detailed cases in Lab2 remain better suited to unit/API tests than UI automation, for example refresh-token handling, invalid callback signatures, rollback-on-failure, retry policy, and channel preference filtering.',
  'The implemented suite is appropriate as function-level automation evidence and can be cited together with the existing unittest/API suite in the project.'
)

$document.SaveAs([ref]$OutputPath, [ref]16)
$document.Close()
$word.Quit()
[System.Runtime.Interopservices.Marshal]::ReleaseComObject($selection) | Out-Null
[System.Runtime.Interopservices.Marshal]::ReleaseComObject($document) | Out-Null
[System.Runtime.Interopservices.Marshal]::ReleaseComObject($word) | Out-Null
[gc]::Collect()
[gc]::WaitForPendingFinalizers()
Write-Output "Generated: $OutputPath"
