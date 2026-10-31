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

# Добавление обработчика спанов
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