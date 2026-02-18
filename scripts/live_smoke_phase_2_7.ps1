$BaseUrl = "http://127.0.0.1:8000"
$ApiKey = "dev-admin-key"
$BusinessId = "11111111-1111-1111-1111-111111111111"
$BranchId = ""
$CashierApiKey = "dev-cashier-key"
$PromptForRestart = $true

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function New-BosHeaders {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Key,
        [bool]$IncludeBranch = $true
    )

    $headers = @{
        "X-API-KEY" = $Key
        "X-BUSINESS-ID" = $BusinessId
        "Accept-Language" = "en"
    }
    if ($IncludeBranch -and $BranchId -and $BranchId.Trim().Length -gt 0) {
        $headers["X-BRANCH-ID"] = $BranchId
    }
    return $headers
}

function Build-Uri {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,
        [hashtable]$Query
    )

    if (-not $Query) {
        return "$BaseUrl$Path"
    }

    $pairs = @()
    foreach ($key in ($Query.Keys | Sort-Object)) {
        $value = $Query[$key]
        if ($null -eq $value) {
            continue
        }
        $text = [string]$value
        if ($text.Length -eq 0) {
            continue
        }
        $pairs += (
            "{0}={1}" -f [System.Uri]::EscapeDataString([string]$key),
            [System.Uri]::EscapeDataString($text)
        )
    }
    if ($pairs.Count -eq 0) {
        return "$BaseUrl$Path"
    }
    return "$BaseUrl$Path?{0}" -f ($pairs -join "&")
}

function Invoke-BosRequest {
    param(
        [Parameter(Mandatory = $true)]
        [ValidateSet("GET", "POST")]
        [string]$Method,
        [Parameter(Mandatory = $true)]
        [string]$Path,
        [Parameter(Mandatory = $true)]
        [hashtable]$Headers,
        [hashtable]$Query,
        $Body
    )

    $uri = Build-Uri -Path $Path -Query $Query
    try {
        if ($null -eq $Body) {
            return Invoke-RestMethod -Method $Method -Uri $uri -Headers $Headers -TimeoutSec 30
        }
        $json = $Body | ConvertTo-Json -Depth 10
        return Invoke-RestMethod -Method $Method -Uri $uri -Headers $Headers -ContentType "application/json" -Body $json -TimeoutSec 30
    } catch {
        $responseBody = $null
        if ($_.Exception.Response -and $_.Exception.Response.GetResponseStream()) {
            $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
            $responseBody = $reader.ReadToEnd()
            $reader.Close()
        }

        if ($responseBody) {
            try {
                return $responseBody | ConvertFrom-Json
            } catch {
                return @{
                    ok = $false
                    error = @{
                        code = "HTTP_ERROR"
                        message = $responseBody
                    }
                }
            }
        }

        return @{
            ok = $false
            error = @{
                code = "HTTP_ERROR"
                message = $_.Exception.Message
            }
        }
    }
}

function Show-Result {
    param(
        [string]$Title,
        $Response
    )

    if ($null -eq $Response) {
        Write-Host "[ERR] $Title -> empty response" -ForegroundColor Yellow
        return
    }
    if ($Response.ok) {
        Write-Host "[OK ] $Title" -ForegroundColor Green
        return
    }

    $code = $Response.error.code
    $message = $Response.error.message
    Write-Host "[ERR] $Title -> $code :: $message" -ForegroundColor Yellow
}

function Assert-OrderedDocs {
    param([array]$Items)

    $previousIssuedAt = $null
    $previousDocId = $null
    foreach ($item in $Items) {
        $issuedAt = [string]$item.issued_at
        $docId = [string]$item.doc_id
        if ($null -ne $previousIssuedAt) {
            if ($issuedAt -lt $previousIssuedAt) {
                return $false
            }
            if ($issuedAt -eq $previousIssuedAt -and $docId -lt $previousDocId) {
                return $false
            }
        }
        $previousIssuedAt = $issuedAt
        $previousDocId = $docId
    }
    return $true
}

Write-Host ""
Write-Host "=== Phase 2.7 Live Smoke (/v1/docs contract lock) ===" -ForegroundColor Cyan
Write-Host "BaseUrl    : $BaseUrl"
Write-Host "BusinessId : $BusinessId"
if ($BranchId -and $BranchId.Trim().Length -gt 0) {
    Write-Host "BranchId   : $BranchId"
}

$adminHeaders = New-BosHeaders -Key $ApiKey -IncludeBranch $true

Write-Host ""
Write-Host "1) Auth smoke (missing API key should fail)"
$authProbe = Invoke-BosRequest -Method "GET" -Path "/v1/docs" -Headers @{ "X-BUSINESS-ID" = $BusinessId } -Query @{ business_id = $BusinessId; limit = 1 } -Body $null
Show-Result -Title "GET /v1/docs without key" -Response $authProbe

Write-Host ""
Write-Host "2) Permission smoke (cashier key on admin endpoint should be denied)"
if ($CashierApiKey -and $CashierApiKey.Trim().Length -gt 0) {
    $cashierHeaders = New-BosHeaders -Key $CashierApiKey -IncludeBranch $false
    $permissionProbe = Invoke-BosRequest -Method "POST" -Path "/v1/admin/roles/assign" -Headers $cashierHeaders -Body @{
        business_id = $BusinessId
        actor_id = "phase27-cashier-probe"
        actor_type = "HUMAN"
        role_name = "CASHIER"
    }
    Show-Result -Title "POST /v1/admin/roles/assign with cashier key" -Response $permissionProbe
} else {
    Write-Host "[SKIP] CashierApiKey not set." -ForegroundColor DarkYellow
}

Write-Host ""
Write-Host "3) Ensure feature flag ENABLE_DOCUMENT_DESIGNER is enabled"
$flagResponse = Invoke-BosRequest -Method "POST" -Path "/v1/admin/feature-flags/set" -Headers $adminHeaders -Body @{
    business_id = $BusinessId
    flag_key = "ENABLE_DOCUMENT_DESIGNER"
    status = "ENABLED"
}
Show-Result -Title "POST /v1/admin/feature-flags/set" -Response $flagResponse

Write-Host ""
Write-Host "4) Bootstrap identity (idempotent)"
$bootstrap = Invoke-BosRequest -Method "POST" -Path "/v1/admin/identity/bootstrap" -Headers $adminHeaders -Body @{
    business_id = $BusinessId
    business_name = "BOS Dev Business"
    default_currency = "USD"
    default_language = "en"
}
Show-Result -Title "POST /v1/admin/identity/bootstrap" -Response $bootstrap

Write-Host ""
Write-Host "5) Issue Receipt / Quote / Invoice"
$branchBody = @{}
if ($BranchId -and $BranchId.Trim().Length -gt 0) {
    $branchBody.branch_id = $BranchId
}

$receiptBody = @{
    business_id = $BusinessId
    payload = @{
        receipt_no = "RCT-2.7-001"
        issued_at = "2026-02-18T10:00:00Z"
        cashier = "Smoke Cashier"
        line_items = @(
            @{
                name = "Item A"
                quantity = 1
                unit_price = 10
                line_total = 10
            }
        )
        subtotal = 10
        tax_total = 1
        grand_total = 11
        notes = "Smoke receipt"
    }
}
$quoteBody = @{
    business_id = $BusinessId
    payload = @{
        quote_no = "QTE-2.7-001"
        issued_at = "2026-02-18T10:01:00Z"
        customer_name = "Smoke Customer"
        line_items = @(
            @{
                sku = "SKU-1"
                description = "Item A"
                quantity = 1
                unit_price = 10
            }
        )
        subtotal = 10
        discount_total = 0
        grand_total = 10
        valid_until = "2026-02-28"
        notes = "Smoke quote"
    }
}
$invoiceBody = @{
    business_id = $BusinessId
    payload = @{
        invoice_no = "INV-2.7-001"
        issued_at = "2026-02-18T10:02:00Z"
        customer_name = "Smoke Customer"
        line_items = @(
            @{
                sku = "SKU-1"
                description = "Item A"
                quantity = 1
                tax = 1
                line_total = 11
            }
        )
        subtotal = 10
        tax_total = 1
        grand_total = 11
        payment_terms = "Due on receipt"
        notes = "Smoke invoice"
    }
}

foreach ($k in $branchBody.Keys) {
    $receiptBody[$k] = $branchBody[$k]
    $quoteBody[$k] = $branchBody[$k]
    $invoiceBody[$k] = $branchBody[$k]
}

$receipt = Invoke-BosRequest -Method "POST" -Path "/v1/docs/receipt/issue" -Headers $adminHeaders -Body $receiptBody
Show-Result -Title "POST /v1/docs/receipt/issue" -Response $receipt

$quote = Invoke-BosRequest -Method "POST" -Path "/v1/docs/quote/issue" -Headers $adminHeaders -Body $quoteBody
Show-Result -Title "POST /v1/docs/quote/issue" -Response $quote

$invoice = Invoke-BosRequest -Method "POST" -Path "/v1/docs/invoice/issue" -Headers $adminHeaders -Body $invoiceBody
Show-Result -Title "POST /v1/docs/invoice/issue" -Response $invoice

$issuedDocIds = @()
foreach ($result in @($receipt, $quote, $invoice)) {
    if ($result.ok -and $result.data.document_id) {
        $issuedDocIds += [string]$result.data.document_id
    }
}

Write-Host ""
Write-Host "6) Read /v1/docs contract (limit=10)"
$docs = Invoke-BosRequest -Method "GET" -Path "/v1/docs" -Headers $adminHeaders -Query @{
    business_id = $BusinessId
    limit = 10
} -Body $null
Show-Result -Title "GET /v1/docs?limit=10" -Response $docs

if ($docs.ok) {
    $items = @($docs.data.items)
    Write-Host ("   count={0} next_cursor={1}" -f $docs.data.count, $docs.data.next_cursor)
    foreach ($item in $items) {
        Write-Host ("   - {0} {1} {2}" -f $item.doc_id, $item.doc_type, $item.issued_at)
    }
    if (Assert-OrderedDocs -Items $items) {
        Write-Host "   ordering check: PASS (issued_at ASC, doc_id ASC)" -ForegroundColor Green
    } else {
        Write-Host "   ordering check: FAIL" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "7) Cursor paging check"
$page1 = Invoke-BosRequest -Method "GET" -Path "/v1/docs" -Headers $adminHeaders -Query @{
    business_id = $BusinessId
    limit = 2
} -Body $null
Show-Result -Title "GET /v1/docs?limit=2" -Response $page1

$cursor = $null
if ($page1.ok) {
    $cursor = $page1.data.next_cursor
    Write-Host ("   next_cursor={0}" -f $cursor)
}

if ($cursor) {
    $page2 = Invoke-BosRequest -Method "GET" -Path "/v1/docs" -Headers $adminHeaders -Query @{
        business_id = $BusinessId
        limit = 2
        cursor = $cursor
    } -Body $null
    Show-Result -Title "GET /v1/docs?limit=2&cursor=..." -Response $page2
}

Write-Host ""
Write-Host "8) Restart persistence proof"
if ($PromptForRestart) {
    Read-Host "Restart server now, then press Enter to continue"
}

$afterRestart = Invoke-BosRequest -Method "GET" -Path "/v1/docs" -Headers $adminHeaders -Query @{
    business_id = $BusinessId
    limit = 50
} -Body $null
Show-Result -Title "GET /v1/docs after restart" -Response $afterRestart

if ($afterRestart.ok) {
    $afterIds = @($afterRestart.data.items | ForEach-Object { [string]$_.doc_id })
    $missing = @($issuedDocIds | Where-Object { $_ -notin $afterIds })
    if ($missing.Count -eq 0) {
        Write-Host "   persistence check: PASS (issued docs still present)" -ForegroundColor Green
    } else {
        Write-Host ("   persistence check: FAIL missing={0}" -f ($missing -join ", ")) -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "Phase 2.7 live smoke completed."
