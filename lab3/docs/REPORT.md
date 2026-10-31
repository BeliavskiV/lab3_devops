# БЕЛОРУССКИЙ ГОСУДАРСТВЕННЫЙ УНИВЕРСИТЕТ
**Факультет прикладной математики и информатики**  
**Кафедра технологий программирования**

## Отчет по лабораторной работе №3
**Тема:** Мониторинг в распределенных системах  
**Дисциплина:** «Непрерывное интегрирование и сборка программного обеспечения»  
**Выполнил:** студент 11 группы Белявский Владислав Алексеевич  
**Вариант:** 1  
**Преподаватель:** ст. преподаватель Давидовская М. И.

Минск, 2026 г.

---

## 1. Цель и задачи работы

### Цель работы
Изучение средств мониторинга для сбора и обработки телеметрии приложений (MLT: Metrics, Logs, Traces) и настройка системы наблюдаемости (Observability), в которой данные метрик, журналов и трассировок собираются для микросервисного приложения на языке Python (фреймворк Flask) с использованием OpenTelemetry, Jaeger, Prometheus, Loki, Promtail и Grafana.

### Задачи работы
1. Подготовить приложение на Python (Flask) к анализу трассировки с помощью **Jaeger**.
2. Упаковать приложение и инфраструктурные компоненты в образы Docker и поднимать на их основе многоконтейнерную систему, используя **Docker Compose**.
3. Обеспечить приложение механизмами экспортирования телеметрии в **Jaeger**, **Prometheus** и **Grafana**.
4. Самостоятельно выполнить сборку метрик, трассировки и журналов по заданию (Вариант 1, группа 11 — выполнение всех 3 заданий).
5. Оформить отчёт в формате Markdown и опубликовать результаты в Git-репозитории.

---

## 2. Вариант задания (Вариант №1)

Для студентов 11 группы (группы 10–12) согласно критериям оценивания выполняются все три задания лабораторной работы:
* **Задание 1 (`/task1`):** Инструментация микросервисного веб-приложения на Flask (`dice-server`) библиотеками OpenTelemetry и экспорт распределённых трассировок в Jaeger.
* **Задание 2 (`/task2`):** Рефакторинг приложения для перехода на протокол OTLP (gRPC), развертывание OpenTelemetry Collector и настройка сбора кастомных метрик (`dice_rolls_total`) в СУБД временных рядов Prometheus.
* **Задание 3 (`/task3`):** Настройка централизованного сбора контейнерных логов с помощью связки Promtail + Grafana Loki и объединение всех трех сигналов наблюдаемости (Metrics, Logs, Traces) в единой панели визуализации Grafana.

---

## 3. Задание 1. Подключение инструментов и библиотек OpenTelemetry и настройка трассировки приложения

### 3.1. Описание шагов выполнения
В рамках первого задания было разработано REST-приложение на базе Flask (`dice-server`), симулирующее бросок игрального кубика по маршруту `/rolldice`. Приложение инструментировано с помощью `FlaskInstrumentor` для автоматического перехвата HTTP-запросов, а также дополнено ручным созданием вложенного спана `roll_dice_operation` с сохранением атрибутов игрока (`player`) и выпавшего значения (`result`).

### 3.2. Исходный код и конфигурационные файлы (`/task1`)

#### Файл `task1/app.py`
```python
import logging
import random
from flask import Flask, request

from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.flask import FlaskInstrumentor

# Настройка ресурсов и TracerProvider
resource = Resource(attributes={SERVICE_NAME: "dice-server"})
provider = TracerProvider(resource=resource)

# Настройка экспортера Jaeger (отправляет данные на порт 6831 по UDP)
jaeger_exporter = JaegerExporter(
    agent_host_name="jaeger",
    agent_port=6831,
)

# Добавление пакетного обработчика спанов
provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))
trace.set_tracer_provider(provider)

tracer = trace.get_tracer(__name__)

app = Flask(__name__)
FlaskInstrumentor().instrument_app(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route("/")
def index():
    return "Welcome to the Dice Rolling Service! Try /rolldice"

@app.route("/rolldice")
def roll_dice():
    with tracer.start_as_current_span("roll_dice_operation") as span:
        player = request.args.get('player', default='Anonymous', type=str)
        result = str(roll())
        
        span.set_attribute("player", player)
        span.set_attribute("result", result)
        
        logger.info(f"Player {player} rolled a {result}")
        return f"{player} rolled: {result}\n"

def roll():
    return random.randint(1, 6)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
```

#### Файл `task1/requirements.txt`
```text
flask==3.0.2
opentelemetry-api==1.22.0
opentelemetry-sdk==1.22.0
opentelemetry-instrumentation-flask==0.43b0
opentelemetry-exporter-jaeger==1.21.0
```

#### Файл `task1/Dockerfile`
```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

EXPOSE 8080

CMD ["python", "app.py"]
```

#### Файл `task1/docker-compose.yml`
```yaml
version: '3.8'

services:
  web:
    build: .
    container_name: flask_trace_app
    ports:
      - "8080:8080"
    environment:
      - OTEL_SERVICE_NAME=dice-server
    depends_on:
      - jaeger
    networks:
      - monitoring

  jaeger:
    image: jaegertracing/all-in-one:1.53
    container_name: jaeger
    ports:
      - "16686:16686"  
      - "6831:6831/udp"
      - "4317:4317"    
      - "4318:4318"   
    networks:
      - monitoring

networks:
  monitoring:
    driver: bridge
```

### 3.3. Протокол выполнения и результаты тестирования (`/task1`)

Сборка и запуск контейнеров в терминале WSL:
```text
user@WIN-RF157T1A1N2:~/lab3/task1$ docker compose up --build -d
[+] Building 37.1s (12/12) FINISHED
 => => naming to docker.io/library/task1-web:latest                                    0.2s
[+] Running 3/3
 ✔ Network task1_monitoring     Created                                                0.0s
 ✔ Container jaeger             Started                                                0.2s
 ✔ Container flask_trace_app    Started                                                0.2s
```

Генерация тестовых HTTP-запросов для проверки трассировки:
```text
user@WIN-RF157T1A1N2:~/lab3/task1$ curl "http://localhost:8080/rolldice?player=Vladislav"
Vladislav rolled: 6
user@WIN-RF157T1A1N2:~/lab3/task1$ curl "http://localhost:8080/rolldice?player=TestUser"
TestUser rolled: 4
```

После отправки запросов в веб-интерфейсе **Jaeger UI** (`http://localhost:16686`) для сервиса `dice-server` были обнаружены трассировки вызовов `/rolldice`. Каждый трейс содержит корневой HTTP-спан Flask и дочерний спан `roll_dice_operation`, внутри которого записаны теги `player="Vladislav"` и `result="6"`.

---

## 4. Задание 2. Настройка сбора метрик приложения

### 4.1. Описание шагов выполнения
Во втором задании произведен рефакторинг приложения: вместо прямой отправки данных в Jaeger настроен экспорт спанов и метрик по универсальному протоколу **OTLP (gRPC)** в промежуточный сборщик **OpenTelemetry Collector** (`otel-collector:4317`). Добавлен счетчик метрик `dice_rolls_total`, фиксирующий количество бросков с разбивкой по имени игрока и выпавшему числу. Сборщик OTel Collector перенаправляет трейсы в Jaeger, а метрики предоставляет на порту `8889` для периодического опроса (scraping) сервером **Prometheus**.

### 4.2. Исходный код и конфигурационные файлы (`/task2`)

#### Файл `task2/app.py`
```python
import logging
import random
from flask import Flask, request

from opentelemetry import trace, metrics
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.instrumentation.flask import FlaskInstrumentor

# Ресурс сервиса
resource = Resource(attributes={SERVICE_NAME: "dice-server"})

# 1. Трассировки (Traces) -> OTLP Collector (gRPC)
tracer_provider = TracerProvider(resource=resource)
otlp_trace_exporter = OTLPSpanExporter(endpoint="otel-collector:4317", insecure=True)
tracer_provider.add_span_processor(BatchSpanProcessor(otlp_trace_exporter))
trace.set_tracer_provider(tracer_provider)
tracer = trace.get_tracer(__name__)

# 2. Метрики (Metrics) -> OTLP Collector (gRPC)
metric_reader = PeriodicExportingMetricReader(
    OTLPMetricExporter(endpoint="otel-collector:4317", insecure=True)
)
meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
metrics.set_meter_provider(meter_provider)
meter = metrics.get_meter(__name__)

# Счетчик для количества бросков кубика
roll_counter = meter.create_counter(
    "dice_rolls_total",
    description="Total number of dice rolls",
    unit="1"
)

# Инициализация Flask
app = Flask(__name__)
FlaskInstrumentor().instrument_app(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route("/")
def index():
    return "Welcome to the Dice Rolling Service! Try /rolldice"

@app.route("/rolldice")
def roll_dice():
    with tracer.start_as_current_span("roll_dice_operation") as span:
        player = request.args.get('player', default='Anonymous', type=str)
        result = str(roll())
        
        span.set_attribute("player", player)
        span.set_attribute("result", result)
        
        # Инкрементируем метрику броска
        roll_counter.add(1, {"player": player, "result": result})
        
        logger.info(f"Player {player} rolled a {result}")
        return f"{player} rolled: {result}\n"

def roll():
    return random.randint(1, 6)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
```

#### Файл `task2/requirements.txt`
```text
flask==3.0.2
opentelemetry-api==1.22.0
opentelemetry-sdk==1.22.0
opentelemetry-instrumentation-flask==0.43b0
opentelemetry-exporter-otlp==1.22.0
```

#### Файл `task2/otel-collector-config.yml`
```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

processors:
  batch:

exporters:
  otlp/jaeger:
    endpoint: jaeger:4317
    tls:
      insecure: true
  prometheus:
    endpoint: "0.0.0.0:8889"
    send_timestamps: true

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch]
      exporters: [otlp/jaeger]
    metrics:
      receivers: [otlp]
      processors: [batch]
      exporters: [prometheus]
```

#### Файл `task2/prometheus.yml`
```yaml
global:
  scrape_interval: 5s

scrape_configs:
  - job_name: 'otel-collector'
    static_configs:
      - targets: ['otel-collector:8889']
```

#### Файл `task2/docker-compose.yml`
```yaml
services:
  web:
    build: .
    container_name: flask_metrics_app
    ports:
      - "8080:8080"
    environment:
      - OTEL_SERVICE_NAME=dice-server
    depends_on:
      - otel-collector
    networks:
      - monitoring

  otel-collector:
    image: otel/opentelemetry-collector-contrib:0.95.0
    container_name: otel-collector
    command: ["--config=/etc/otel-collector-config.yml"]
    volumes:
      - ./otel-collector-config.yml:/etc/otel-collector-config.yml
    ports:
      - "4317:4317"
      - "4318:4318"
      - "8889:8889"
    depends_on:
      - jaeger
    networks:
      - monitoring

  jaeger:
    image: jaegertracing/all-in-one:1.53
    container_name: jaeger
    ports:
      - "16686:16686"
      - "4317"
    networks:
      - monitoring

  prometheus:
    image: prom/prometheus:v2.50.1
    container_name: prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"
    networks:
      - monitoring

networks:
  monitoring:
    driver: bridge
```

### 4.3. Протокол выполнения и результаты тестирования (`/task2`)

Запуск стека и проверка статуса контейнеров:
```text
user@WIN-RF157T1A1N2:~/lab3/task2$ docker compose up --build -d
user@WIN-RF157T1A1N2:~/lab3/task2$ docker compose ps
NAME                IMAGE                                       STATUS
flask_metrics_app   task2-web                                   Up 12 seconds
jaeger              jaegertracing/all-in-one:1.53               Up 14 seconds
otel-collector      otel/opentelemetry-collector-contrib:0.95.0 Up 13 seconds
prometheus          prom/prometheus:v2.50.1                     Up 14 seconds
```

Генерация метрик с помощью HTTP-запросов:
```text
user@WIN-RF157T1A1N2:~/lab3/task2$ curl "http://localhost:8080/rolldice?player=Vladislav"
Vladislav rolled: 1
user@WIN-RF157T1A1N2:~/lab3/task2$ curl "http://localhost:8080/rolldice?player=Vladislav"
Vladislav rolled: 5
user@WIN-RF157T1A1N2:~/lab3/task2$ curl "http://localhost:8080/rolldice?player=Alex"
Alex rolled: 1
```

Результаты выполнения PromQL-запроса `dice_rolls_total` в веб-интерфейсе **Prometheus UI** (`http://localhost:9090`):
```text
dice_rolls_total{exported_job="dice-server", instance="otel-collector:8889", job="otel-collector", player="Alex", result="1"}       1
dice_rolls_total{exported_job="dice-server", instance="otel-collector:8889", job="otel-collector", player="Vladislav", result="1"}  1
dice_rolls_total{exported_job="dice-server", instance="otel-collector:8889", job="otel-collector", player="Vladislav", result="5"}  1
```

---

## 5. Задание 3. Анализ журналов, визуализация и исследование телеметрии

### 5.1. Описание шагов выполнения
В третьем задании развернут полный стек наблюдаемости (Observability Stack), объединяющий **Traces**, **Metrics** и **Logs**:
* Агент **Promtail** подключается к сокету `/var/run/docker.sock`, автоматически обнаруживает запущенные Docker-контейнеры, извлекает их потоки `stdout`/`stderr`, маркирует меткой `container` и пересылает в **Grafana Loki**.
* Система визуализации **Grafana** объединяет три источника данных: Prometheus (`http://prometheus:9090`), Loki (`http://loki:3100`) и Jaeger (`http://jaeger:16686`).

### 5.2. Конфигурационные файлы (`/task3`)

#### Файл `task3/loki-config.yml`
```yaml
auth_enabled: false

server:
  http_listen_port: 3100

common:
  path_prefix: /tmp/loki
  storage:
    filesystem:
      chunks_directory: /tmp/loki/chunks
      rules_directory: /tmp/loki/rules
  replication_factor: 1
  ring:
    kvstore:
      store: inmemory

schema_config:
  configs:
    - from: 2020-05-15
      store: tsdb
      object_store: filesystem
      schema: v13
      index:
        prefix: index_
        period: 24h
```

#### Файл `task3/promtail-config.yml`
```yaml
server:
  http_listen_port: 9080
  grpc_listen_port: 0

positions:
  filename: /tmp/positions.yaml

clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
  - job_name: docker
    docker_sd_configs:
      - host: unix:///var/run/docker.sock
        refresh_interval: 5s
    relabel_configs:
      - source_labels: ['__meta_docker_container_name']
        regex: '/(.*)'
        target_label: 'container'
```

#### Файл `task3/docker-compose.yml`
```yaml
services:
  web:
    build: .
    container_name: flask_observability_app
    ports:
      - "8080:8080"
    environment:
      - OTEL_SERVICE_NAME=dice-server
    depends_on:
      - otel-collector
    networks:
      - monitoring

  otel-collector:
    image: otel/opentelemetry-collector-contrib:0.95.0
    container_name: otel-collector
    command: ["--config=/etc/otel-collector-config.yml"]
    volumes:
      - ./otel-collector-config.yml:/etc/otel-collector-config.yml
    ports:
      - "4317:4317"
      - "4318:4318"
      - "8889:8889"
    depends_on:
      - jaeger
    networks:
      - monitoring

  jaeger:
    image: jaegertracing/all-in-one:1.53
    container_name: jaeger
    ports:
      - "16686:16686"
      - "4317"
    networks:
      - monitoring

  prometheus:
    image: prom/prometheus:v2.50.1
    container_name: prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"
    networks:
      - monitoring

  loki:
    image: grafana/loki:2.9.4
    container_name: loki
    ports:
      - "3100:3100"
    command: -config.file=/etc/loki/local-config.yaml
    volumes:
      - ./loki-config.yml:/etc/loki/local-config.yaml
    networks:
      - monitoring

  promtail:
    image: grafana/promtail:2.9.4
    container_name: promtail
    volumes:
      - ./promtail-config.yml:/etc/promtail/config.yml
      - /var/run/docker.sock:/var/run/docker.sock
    command: -config.file=/etc/promtail/config.yml
    depends_on:
      - loki
    networks:
      - monitoring

  grafana:
    image: grafana/grafana:10.3.3
    container_name: grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=admin
    depends_on:
      - prometheus
      - loki
      - jaeger
    networks:
      - monitoring

networks:
  monitoring:
    driver: bridge
```

### 5.3. Протокол выполнения и результаты тестирования (`/task3`)

Запуск всех 7 сервисов и проверка их состояния:
```text
user@WIN-RF157T1A1N2:~/lab3/task3$ docker compose up --build -d
user@WIN-RF157T1A1N2:~/lab3/task3$ docker compose ps
NAME                      IMAGE                                         SERVICE          STATUS         PORTS
flask_observability_app   task3-web                                     web              Up 10 seconds  0.0.0.0:8080->8080/tcp
grafana                   grafana/grafana:10.3.3                        grafana          Up 10 seconds  0.0.0.0:3000->3000/tcp
jaeger                    jaegertracing/all-in-one:1.53                 jaeger           Up 11 seconds  0.0.0.0:16686->16686/tcp
loki                      grafana/loki:2.9.4                            loki             Up 11 seconds  0.0.0.0:3100->3100/tcp
otel-collector            otel/opentelemetry-collector-contrib:0.95.0   otel-collector   Up 10 seconds  0.0.0.0:4317-4318->4317-4318/tcp, 0.0.0.0:8889->8889/tcp
prometheus                prom/prometheus:v2.50.1                       prometheus       Up 11 seconds  0.0.0.0:9090->9090/tcp
promtail                  grafana/promtail:2.9.4                        promtail         Up 10 seconds
```

Отправка запросов к приложению:
```text
user@WIN-RF157T1A1N2:~/lab3/task3$ curl http://localhost:8080/
Welcome to the Dice Rolling Service! Try /rolldice
user@WIN-RF157T1A1N2:~/lab3/task3$ curl http://localhost:8080/rolldice
Anonymous rolled: 3
user@WIN-RF157T1A1N2:~/lab3/task3$ curl "http://localhost:8080/rolldice?player=Vladislav"
Vladislav rolled: 4
```

В веб-интерфейсе **Grafana** (`http://localhost:3000`) подключены три источника данных (Prometheus, Loki, Jaeger). В разделе **Explore** для источника Loki выполнен LogQL-запрос `{container="flask_observability_app"}`, который вывел строки лога:
`INFO:app:Player Vladislav rolled a 4`. Таким образом, метрики, логи и трассировки приложения агрегируются и визуализируются в единой системе.

---

## 6. Ответы на контрольные вопросы

### 1. Что такое OpenTelemetry? Атрибуты, события, контекст, журналы, трассировки, показатели?
**OpenTelemetry (OTel)** — это открытый стандарт и фреймворк наблюдаемости (проект CNCF), предоставляющий унифицированный набор API, SDK, протоколов (OTLP) и инструментов для генерации, сбора и экспорта телеметрических данных из облачных и распределенных приложений.
* **Атрибуты (Attributes):** Пары «ключ-значение», содержащие метаданные для обогащения спанов, метрик или логов (например, `http.status_code=200`, `player="Vladislav"`).
* **События (Events):** Структурированные записи с временной меткой внутри спана, фиксирующие конкретное происшествие в ходе выполнения операции (например, возникновение исключения).
* **Контекст (Context):** Неизменяемый объект, передаваемый внутри процесса и между сервисами по сети (Context Propagation через заголовки W3C `traceparent`), связывающий отдельные спаны в единую распределенную трассировку (`Trace ID`, `Span ID`).
* **Журналы (Logs):** Текстовые или структурированные записи о дискретных событиях с привязкой ко времени.
* **Трассировки (Traces):** Представление полного пути прохождения запроса через узлы распределенной системы, состоящее из иерархии спанов (Spans).
* **Показатели / Метрики (Metrics):** Числовые агрегированные измерения состояния ресурсов или бизнес-логики за интервал времени.

### 2. Что такое наблюдаемость? Надежность и показатели?
* **Наблюдаемость (Observability):** Способность оценивать внутреннее состояние сложной системы исключительно по её внешним выходным сигналам (метрикам, журналам и трассировкам).
* **Надежность (Reliability):** Свойство системы безотказно выполнять заданные функции в течение определенного периода времени при заданных условиях эксплуатации.
* **Показатели надежности (SLI, SLO, SLA):**
  * **SLI (Service Level Indicator)** — конкретная измеряемая метрика качества работы сервиса (например, доля успешных HTTP-ответов или 95-й перцентиль задержки).
  * **SLO (Service Level Objective)** — целевой диапазон значений для SLI (например, $\text{SLI} \ge 99.9\%$ за месяц).
  * **SLA (Service Level Agreement)** — юридическое или бизнес-соглашение с клиентом, фиксирующее последствия нарушения SLO.

### 3. Что такое трассировка? Что такое распределенная трассировка? Как собирать распределенную трассировку и какие проблемы имеются в распределенной архитектуре?
* **Трассировка (Tracing):** Запись последовательности вызовов функций и длительности операций в рамках обработки одного запроса.
* **Распределенная трассировка (Distributed Tracing):** Метод отслеживания сквозного пути запроса, проходящего через множество независимых микросервисов, очередей сообщений и баз данных.
* **Как собирать:** Каждый сервис инструментируется библиотекой OpenTelemetry; при входящем запросе сервис извлекает `Trace ID` и родительский `Span ID` из сетевых заголовков, создает дочерний спан и передает контекст дальше при исходящих вызовах, а завершенные спаны асинхронно отправляет в коллектор (Jaeger/Tempo).
* **Проблемы в распределенной архитектуре:** Сетевые задержки, потеря контекста при асинхронном взаимодействии через брокеры сообщений, рассинхронизация часов на разных серверах (clock skew) и огромный объем генерируемых данных (требующий применения стратегий сэмплирования — Head-based или Tail-based sampling).

### 4. Сигналы OpenTelemetry: трассировки, метрики, логи?
Три базовых столпа телеметрии (MLT) в OpenTelemetry:
1. **Метрики (Metrics):** Отвечают на вопрос *«Есть ли проблема и насколько она масштабна?»* (агрегированные числа: RPS, процент ошибок, утилизация CPU/RAM).
2. **Трассировки (Traces):** Отвечают на вопрос *«Где именно (в каком сервисе и методе) возникла задержка или сбой?»*.
3. **Логи (Logs):** Отвечают на вопрос *«Почему произошла ошибка?»* (детальный стек-трейс и параметры вызова в конкретной точке).

### 5. Инструменты OpenTelemetry: автоматические, ручные, библиотеки?
* **Автоматическая инструментация (Auto-instrumentation):** Подключение агентов или оберток (`opentelemetry-instrument`, `FlaskInstrumentor`), которые автоматически перехватывают запросы популярных фреймворков, HTTP-клиентов и драйверов БД без модификации бизнес-кода.
* **Ручная инструментация (Manual instrumentation):** Явный вызов OpenTelemetry API разработчиком в коде (`tracer.start_as_current_span()`, `counter.add()`) для отслеживания специфической бизнес-логики.
* **Библиотеки (API и SDK):** API предоставляет интерфейсы для встраивания в код (безопасные и не влияющие на работу без SDK), а SDK реализует фактическую обработку, сэмплирование, агрегацию и экспорт данных.

### 6. Компоненты OpenTelemetry: спецификация, сборщики, библиотеки инструментальных средств, экспортеры, автоматические измерительные инструменты?
* **Спецификация (Specification):** Языково-независимый документ, определяющий модель данных, семантические соглашения (Semantic Conventions) и архитектуру API/SDK.
* **Сборщики (OpenTelemetry Collector):** Независимый от вендора прокси-сервис, который принимает телеметрию (Receivers), фильтрует и группирует её (Processors) и рассылает в одно или несколько хранилищ (Exporters).
* **Библиотеки инструментальных средств (Instrumentation Libraries):** Готовые плагины для конкретных фреймворков (Flask, FastAPI, Requests, SQLAlchemy).
* **Экспортеры (Exporters):** Модули, преобразующие внутреннее представление OTel в формат целевой системы (OTLP, Jaeger, Prometheus, Zipkin).
* **Автоматические измерительные инструменты:** CLI-утилиты и байткод-агенты для бесшовного внедрения телеметрии при запуске процесса.

### 7. Ресурс OpenTelemetry (телеметрия)?
**Resource (Ресурс)** в OpenTelemetry — это неизменяемый набор атрибутов, описывающий саму сущность (процесс, контейнер, хост, облачную функцию), которая порождает телеметрию. Ключевые атрибуты ресурса: `service.name` (например, `dice-server`), `service.version`, `deployment.environment`, `host.name`.

### 8. Экспортеры OpenTelemetry?
Экспортеры отвечают за отправку батчей спанов, метрик и логов из SDK приложения или из OTel Collector во внешние системы хранения:
* **OTLP Exporter (`OTLPSpanExporter`, `OTLPMetricExporter`):** Стандартный экспортер по протоколу OpenTelemetry Protocol (поверх gRPC или HTTP/Protobuf).
* **Специализированные экспортеры:** `JaegerExporter`, `PrometheusExporter` (поднимает HTTP-эндпоинт для чтения метрик), `ZipkinExporter`.
* **Отладочные экспортеры:** `ConsoleSpanExporter` / `ConsoleMetricExporter` (выводят телеметрию в стандартный поток вывода `stdout`).

### 9. Что такое Prometheus? Как работает Prometheus?
**Prometheus** — это система мониторинга и база данных временных рядов (Time Series Database — TSDB) с открытым исходным кодом.
*Принцип работы:* Prometheus использует **Pull-модель (опрос)**. Сервер Prometheus с заданным интервалом (`scrape_interval`) обращается по HTTP к сконфигурированным целям (`targets`, например `otel-collector:8889/metrics`), парсит текстовый формат метрик и сохраняет значения с временной меткой в локальное дисковое хранилище.

### 10. Концепции Prometheus?
* **Модель данных (Time Series):** Каждая временная серия уникально идентифицируется именем метрики и набором меток в формате `metric_name{label1="val1", label2="val2"}`.
* **Jobs and Instances:** `Instance` — отдельный опрашиваемый эндпоинт; `Job` — группа однотипных инстансов (например, реплики одного сервиса).
* **PromQL (Prometheus Query Language):** Функциональный язык запросов для фильтрации, агрегации и вычисления производных величин по временным рядам в реальном времени.
* **Alertmanager:** Компонент для обработки сработавших правил оповещений (дедупликация, группировка и отправка уведомлений в Telegram, Slack, Email).

### 11. Типы метрик?
В Prometheus и OpenTelemetry выделяют 4 основных типа метрик:
1. **Counter (Счётчик):** Монотонно возрастающая кумулятивная метрика (может только увеличиваться или сбрасываться в ноль при рестарте процесса). Пример: общее число запросов `dice_rolls_total`.
2. **Gauge (Датчик / Измеритель):** Числовой показатель, который может как расти, так и уменьшаться. Пример: текущее использование оперативной памяти, температура, число активных соединений.
3. **Histogram (Гистограмма):** Распределяет измеряемые величины (обычно время ответа или размер запроса) по заранее заданным корзинам (`buckets`), а также хранит общую сумму и количество измерений.
4. **Summary (Сводка):** Похожа на гистограмму, но вычисляет квантили ($\varphi$-квантили, например $p95, p99$) непосредственно на стороне клиентского приложения за скользящее окно времени.

### 12. Запрос и преобразование данных Grafana?
* **Запросы (Queries):** В редакторе панели Grafana пользователь формирует запрос на языке выбранного источника данных (PromQL для Prometheus, LogQL для Loki, поиск по тегам для Jaeger). Можно комбинировать несколько запросов (`A`, `B`, `C`) на одном графике.
* **Преобразования (Transformations):** Конвейер постобработки данных внутри самой Grafana перед их отрисовкой: объединение таблиц (*Join by field*), фильтрация полей, вычисление новых колонок (*Add field from calculation*), транспонирование и переименование серий.

### 13. Источники данных Grafana?
**Data Sources (Источники данных)** — это подключаемые модули, через которые Grafana запрашивает данные для визуализации без необходимости дублировать их в собственной БД:
* **Временные ряды и метрики:** Prometheus, InfluxDB, VictoriaMetrics, Graphite.
* **Логи и документы:** Grafana Loki, Elasticsearch, OpenSearch.
* **Трассировки:** Jaeger, Grafana Tempo, Zipkin.
* **Реляционные СУБД:** PostgreSQL, MySQL, MS SQL.

### 14. Панели мониторинга Grafana?
**Dashboards (Дашборды)** состоят из сетки виджетов (**Panels**), поддерживают шаблонизацию через переменные (Variables), выбор временного диапазона и автообновление. Основные виды панелей:
* **Time series** — графики изменения метрик во времени;
* **Stat / Gauge / Bar gauge** — крупные индикаторы текущих пороговых значений;
* **Logs** — интерактивный просмотр потока журналов с подсветкой уровней (`INFO`, `WARN`, `ERROR`);
* **Node Graph / Trace View** — граф зависимостей микросервисов и диаграмма Ганта для спанов трассировки.

### 15. Процесс обработки журналов Grafana Loki?
Архитектура Loki построена по принципу *«Like Prometheus, but for logs»*:
1. **Сбор и парсинг (Promtail):** Агент обнаруживает контейнеры или лог-файлы, считывает новые строки и формирует набор метаданных-меток (`labels`, например `container`, `job`, `env`).
2. **Отправка (Push API):** Пакеты строк со штампом времени и метками отправляются по HTTP POST на `/loki/api/v1/push`.
3. **Индексация только метаданных:** В отличие от Elasticsearch, Loki **не делает полнотекстовую индексацию** содержимого логов. Индексируется только компактный набор меток (в формате TSDB), что радикально снижает потребление RAM и диска.
4. **Хранение чанков (Chunks):** Сжатые блоки сырого текста логов с одинаковым набором меток сбрасываются на диск или в объектное хранилище (S3/MinIO).
5. **Чтение (LogQL):** При запросе в Grafana Loki сначала по индексу меток быстро находит нужные чанки за выбранный интервал времени, а затем параллельно сканирует их содержимое (grep/парсинг JSON/регулярные выражения).

### 16. Варианты сборки журналов для Grafana Loki?
Доставить логи в Loki можно несколькими способами:
1. **Promtail:** Классический специализированный агент доставки логов из локальных файлов, `systemd journal` и сокета Docker/Kubernetes.
2. **Grafana Alloy (ранее Grafana Agent):** Современный единый агент на базе конвейеров для сбора сразу всех сигналов (Metrics, Logs, Traces, Profiles).
3. **Docker Logging Driver Plugin:** Официальный плагин драйвера логирования Docker, отправляющий вывод контейнеров напрямую в Loki без отдельного контейнера-агента.
4. **OpenTelemetry Collector / Fluent Bit / Vector:** Использование сторонних высокопроизводительных коллекторов со встроенным экспортером в формат Loki.