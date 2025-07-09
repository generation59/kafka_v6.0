# PowerShell скрипт для запуска аналитической платформы маркетплейса

Write-Host "🚀 Запуск аналитической платформы маркетплейса" -ForegroundColor Green
Write-Host "=============================================="

# Функция для проверки доступности сервиса
function Wait-ForService {
    param(
        [string]$ServiceName,
        [int]$Port,
        [int]$MaxAttempts = 30
    )
    
    Write-Host "⏳ Ожидание запуска $ServiceName на порту $Port..." -ForegroundColor Yellow
    
    for ($attempt = 1; $attempt -le $MaxAttempts; $attempt++) {
        try {
            $connection = Test-NetConnection -ComputerName localhost -Port $Port -WarningAction SilentlyContinue
            if ($connection.TcpTestSucceeded) {
                Write-Host "✅ $ServiceName доступен!" -ForegroundColor Green
                return $true
            }
        }
        catch {
            # Игнорируем ошибки подключения
        }
        
        Write-Host "   Попытка $attempt/$MaxAttempts..."
        Start-Sleep -Seconds 5
    }
    
    Write-Host "❌ $ServiceName не удалось запустить в отведенное время" -ForegroundColor Red
    return $false
}

# Функция для проверки Docker образов
function Test-DockerImages {
    Write-Host "🔍 Проверка Docker образов..." -ForegroundColor Cyan
    
    $requiredImages = @(
    "confluentinc/cp-zookeeper:7.4.3",
    "confluentinc/cp-kafka:7.4.3",
    "confluentinc/cp-kafka-connect:7.4.3",
    "prom/prometheus:v2.48.0",
    "grafana/grafana:10.2.0",
    "prom/alertmanager:v0.26.0",
    # "docker.elastic.co/elasticsearch/elasticsearch:8.11.1",  # Отключено из-за блокировки CloudFront
    "bitnami/spark:3.5.0"
)
    
    foreach ($image in $requiredImages) {
        $result = docker image inspect $image 2>$null
        if ($LASTEXITCODE -ne 0) {
            Write-Host "⬇️  Загрузка образа $image..." -ForegroundColor Yellow
            docker pull $image
        }
    }
    
    Write-Host "✅ Все Docker образы готовы" -ForegroundColor Green
}

# 1. Проверка зависимостей
Write-Host "1️⃣  Проверка зависимостей..." -ForegroundColor Cyan

# Проверка Docker
try {
    $dockerVersion = docker --version
    Write-Host "✅ Docker установлен: $dockerVersion" -ForegroundColor Green
}
catch {
    Write-Host "❌ Docker не установлен" -ForegroundColor Red
    exit 1
}

# Проверка Docker Compose
try {
    $composeVersion = docker compose version
    Write-Host "✅ Docker Compose установлен" -ForegroundColor Green
}
catch {
    Write-Host "❌ Docker Compose не установлен" -ForegroundColor Red
    exit 1
}

Test-DockerImages

# 2. Остановка существующих контейнеров
Write-Host "2️⃣  Остановка существующих контейнеров..." -ForegroundColor Cyan
docker compose down -v 2>$null

# 3. Создание необходимых директорий
Write-Host "3️⃣  Создание директорий..." -ForegroundColor Cyan
New-Item -ItemType Directory -Force -Path "data/kafka-connect-data" | Out-Null
New-Item -ItemType Directory -Force -Path "data/output" | Out-Null

# 4. Запуск инфраструктуры
Write-Host "4️⃣  Запуск инфраструктуры..." -ForegroundColor Cyan
docker compose up -d

# 5. Ожидание запуска сервисов
Write-Host "5️⃣  Ожидание запуска сервисов..." -ForegroundColor Cyan

$services = @(
    @{Name="Zookeeper"; Port=2181},
    @{Name="Kafka Broker 1"; Port=9092},
    @{Name="Kafka Broker 2"; Port=9093}, 
    @{Name="Kafka Broker 3"; Port=9094},
    @{Name="Kafka Connect"; Port=8083},
    @{Name="Prometheus"; Port=9090},
    @{Name="Grafana"; Port=3000},
            @{Name="Alertmanager"; Port=9394},

    @{Name="Spark Master"; Port=8080}
)

foreach ($service in $services) {
    Wait-ForService -ServiceName $service.Name -Port $service.Port
}

# 6. Настройка Kafka топиков
Write-Host "6️⃣  Настройка Kafka топиков..." -ForegroundColor Cyan

# Функция создания топика
function New-KafkaTopic {
    param(
        [string]$TopicName,
        [int]$Partitions = 6,
        [int]$Replication = 3
    )
    
    Write-Host "Создание топика: $TopicName (партиции: $Partitions, репликация: $Replication)"
    
    docker exec kafka-broker-1 kafka-topics.sh `
        --create `
        --topic $TopicName `
        --bootstrap-server localhost:9092 `
        --partitions $Partitions `
        --replication-factor $Replication `
        --config min.insync.replicas=2 `
        --if-not-exists
}

# Создание основных топиков
New-KafkaTopic -TopicName "shop-products" -Partitions 6 -Replication 3
New-KafkaTopic -TopicName "filtered-products" -Partitions 6 -Replication 3
New-KafkaTopic -TopicName "filtered-events" -Partitions 3 -Replication 3
New-KafkaTopic -TopicName "client-searches" -Partitions 3 -Replication 3
New-KafkaTopic -TopicName "client-recommendations" -Partitions 3 -Replication 3
New-KafkaTopic -TopicName "recommendations-results" -Partitions 3 -Replication 3

# Служебные топики
New-KafkaTopic -TopicName "docker-connect-configs" -Partitions 1 -Replication 3
New-KafkaTopic -TopicName "docker-connect-offsets" -Partitions 25 -Replication 3
New-KafkaTopic -TopicName "docker-connect-status" -Partitions 5 -Replication 3

# 7. Настройка Kafka Connect
Write-Host "7️⃣  Настройка Kafka Connect..." -ForegroundColor Cyan
Start-Sleep -Seconds 10

Write-Host "Создание File Sink коннектора..."
try {
    $connectorConfig = Get-Content "config/file-sink-connector.json" -Raw
    $response = Invoke-RestMethod -Uri "http://localhost:8083/connectors" -Method Post -Body $connectorConfig -ContentType "application/json"
    Write-Host "✅ Коннектор создан" -ForegroundColor Green
}
catch {
    Write-Host "⚠️  Не удалось создать коннектор (возможно, уже существует)" -ForegroundColor Yellow
}

# 8. Проверка статуса
Write-Host "8️⃣  Проверка статуса системы..." -ForegroundColor Cyan

Write-Host ""
Write-Host "📊 Статус сервисов:" -ForegroundColor Cyan
Write-Host "==================="

# Проверка сервисов
$kafkaStatus = Test-NetConnection -ComputerName localhost -Port 9092 -WarningAction SilentlyContinue
if ($kafkaStatus.TcpTestSucceeded) {
    Write-Host "✅ Kafka Cluster: работает" -ForegroundColor Green
}
else {
    Write-Host "❌ Kafka Cluster: недоступен" -ForegroundColor Red
}

try {
    $connectResponse = Invoke-RestMethod -Uri "http://localhost:8083/connectors" -Method Get
    Write-Host "✅ Kafka Connect: работает" -ForegroundColor Green
    Write-Host "   Коннекторы: $($connectResponse.Count) активных"
}
catch {
    Write-Host "❌ Kafka Connect: недоступен" -ForegroundColor Red
}

try {
    $prometheusResponse = Invoke-RestMethod -Uri "http://localhost:9090/-/healthy" -Method Get
    Write-Host "✅ Prometheus: работает" -ForegroundColor Green
}
catch {
    Write-Host "❌ Prometheus: недоступен" -ForegroundColor Red
}

try {
    $grafanaResponse = Invoke-RestMethod -Uri "http://localhost:3000/api/health" -Method Get
    Write-Host "✅ Grafana: работает (admin/grafana)" -ForegroundColor Green
}
catch {
    Write-Host "❌ Grafana: недоступен" -ForegroundColor Red
}

Write-Host "✅ Поиск товаров: файловый (Elasticsearch отключен)" -ForegroundColor Green

$sparkStatus = Test-NetConnection -ComputerName localhost -Port 8080 -WarningAction SilentlyContinue
if ($sparkStatus.TcpTestSucceeded) {
    Write-Host "✅ Spark Master: работает" -ForegroundColor Green
}
else {
    Write-Host "❌ Spark Master: недоступен" -ForegroundColor Red
}

Write-Host ""
Write-Host "🎯 Веб-интерфейсы:" -ForegroundColor Cyan
Write-Host "=================="
Write-Host "• Grafana:        http://localhost:3000 (admin/grafana)"
Write-Host "• Prometheus:     http://localhost:9090"
    Write-Host "• Alertmanager:   http://localhost:9394"
Write-Host "• Spark Master:   http://localhost:8080"
Write-Host "• Kafka Connect:  http://localhost:8083"

Write-Host ""
Write-Host "🔧 Команды для работы с системой:" -ForegroundColor Cyan
Write-Host "================================="
Write-Host "• Запуск Shop API:        python -m src.shop_api.producer"
Write-Host "• Запуск Client API:      python -m src.client_api.client search 'умные часы'"
Write-Host "• Запуск Stream Filter:   python -m src.stream_processor.banned_filter start"
Write-Host "• Запуск Analytics:       python -m src.analytics.spark_analytics start"
Write-Host "• Управление банами:      python -m src.stream_processor.banned_filter ban --product-id 'ID'"

Write-Host ""
Write-Host "✅ Система запущена и готова к работе!" -ForegroundColor Green
Write-Host ""
Write-Host "📝 Для остановки системы выполните: docker compose down" -ForegroundColor Yellow 