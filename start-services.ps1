# Start all Kaizen services
Write-Host "Starting Kaizen services..." -ForegroundColor Green

# Check if Docker is running
try {
    docker ps | Out-Null
    Write-Host "✓ Docker is running" -ForegroundColor Green
} catch {
    Write-Host "✗ Docker is not running. Please start Docker Desktop first." -ForegroundColor Red
    exit 1
}

# Navigate to project directory
Set-Location $PSScriptRoot

# Build and start services
Write-Host "`nBuilding and starting services..." -ForegroundColor Yellow
docker-compose up -d --build

# Wait a moment for services to initialize
Start-Sleep -Seconds 5

# Check service status
Write-Host "`nService Status:" -ForegroundColor Cyan
docker-compose ps

Write-Host "`n✓ Services are starting!" -ForegroundColor Green
Write-Host "Frontend: http://localhost" -ForegroundColor Cyan
Write-Host "Service A API: http://localhost/api" -ForegroundColor Cyan
Write-Host "Service B API: http://localhost (internal)" -ForegroundColor Cyan
Write-Host "`nTo view logs: docker-compose logs -f" -ForegroundColor Yellow
Write-Host "To stop services: docker-compose down" -ForegroundColor Yellow

