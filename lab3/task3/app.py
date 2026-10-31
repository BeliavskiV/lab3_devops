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