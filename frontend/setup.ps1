$ErrorActionPreference = "Stop"
Write-Host "Installing dependencies..." -ForegroundColor Cyan
npm install
Write-Host "Starting Vite once will generate src/routeTree.gen.ts." -ForegroundColor Green
Write-Host "Run: npm run dev" -ForegroundColor Yellow
