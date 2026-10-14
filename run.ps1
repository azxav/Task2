$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
Set-Location -LiteralPath $root
$env:OLLAMA_HOST = '127.0.0.1:11435'
$env:OLLAMA_MODELS = Join-Path $root '.cache/ollama-models'
$env:OLLAMA_MAX_LOADED_MODELS = '1'
$env:OLLAMA_NUM_PARALLEL = '1'
$env:OLLAMA_CONTEXT_LENGTH = '4096'
$env:OLLAMA_NO_CLOUD = '1'
$env:OLLAMA_VULKAN = '0'
$env:DOC_TASKS_OLLAMA_URL = 'http://127.0.0.1:11435'
$env:HF_HUB_OFFLINE = '1'
$env:TRANSFORMERS_OFFLINE = '1'
$env:PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK = 'True'
try {
    Invoke-RestMethod 'http://127.0.0.1:11435/api/version' -TimeoutSec 3 | Out-Null
} catch {
    $ollamaBinary = Join-Path $root '.cache/runtime/ollama/ollama.exe'
    if (-not (Test-Path -LiteralPath $ollamaBinary)) { throw 'Tested portable Ollama runtime absent. See README.md.' }
    $ollamaHelper = Start-Process -FilePath $ollamaBinary -ArgumentList 'serve' -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $root '.cache/runtime/ollama.stdout.log') -RedirectStandardError (Join-Path $root '.cache/runtime/ollama.stderr.log')
    Set-Content -LiteralPath (Join-Path $root '.cache/runtime/ollama.pid') -Value $ollamaHelper.Id
    for ($attempt=0; $attempt -lt 20; $attempt++) {
        try { Invoke-RestMethod 'http://127.0.0.1:11435/api/version' -TimeoutSec 2 | Out-Null; break } catch { Start-Sleep -Milliseconds 500 }
    }
}
uv run doc-tasks serve --port 8132
