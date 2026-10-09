# Dot-source before build or UAT. Only this process and its children are changed.
$workspace = 'H:\AI-Workspace'
. (Join-Path $workspace 'dev-env.ps1')
$env:AI_WORKSPACE = $workspace
$env:JIANGYI_STAGE3_ROOT = Join-Path $workspace 'uat\xml-uat\stage3-expansion'
$env:PLAYWRIGHT_CLI_PATH = Join-Path $workspace 'caches\npm\_npx\31e32ef8478fbf80\node_modules\@playwright\cli\playwright-cli.js'
$env:LOCALAPPDATA = Join-Path $workspace 'uat\product-defect-closeout-20261009\profile'
$env:C4_REPO_ROOT = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
if (-not (Test-Path -LiteralPath $env:PLAYWRIGHT_CLI_PATH -PathType Leaf)) {
    throw 'Reviewed Playwright CLI is missing from the migrated npm cache.'
}
