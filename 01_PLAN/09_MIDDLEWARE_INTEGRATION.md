# AIFlow - Middleware Integracio (Kafka es mas)

## 1. Adapter Pattern

### 1.1 MessageBroker Absztrakt Interface

```python
# src/aiflow/execution/messaging.py
class MessageBroker(ABC):
    """Absztrakt interface uzenetsor integraciohoz."""

    @abstractmethod
    async def publish(self, topic: str, message: bytes,
                      key: str | None = None,
                      headers: dict[str, str] | None = None) -> None: ...

    @abstractmethod
    async def subscribe(self, topic: str, group_id: str) -> AsyncIterator[Message]: ...

    @abstractmethod
    async def acknowledge(self, message: Message) -> None: ...

    @abstractmethod
    async def health_check(self) -> bool: ...

class Message(BaseModel):
    topic: str
    key: str | None
    value: bytes
    headers: dict[str, str]
    offset: int | None = None
    timestamp: datetime
```

### 1.2 Konkret Adapter-ek

```
src/aiflow/contrib/messaging/
    redis_streams.py      # Default - nulla konfiguracio (meglevo Redis)
    kafka.py              # Apache Kafka (aiokafka)
    rabbitmq.py           # RabbitMQ (aio-pika)
    azure_servicebus.py   # Azure Service Bus
    aws_sqs.py            # AWS SQS (aiobotocore)
```

### 1.3 Konfiguracio

```yaml
# aiflow.yaml
messaging:
  broker: kafka                        # redis_streams | kafka | rabbitmq | azure_servicebus | aws_sqs
  kafka:
    bootstrap_servers: "kafka:9092"
    schema_registry_url: "http://schema-registry:8081"
    security_protocol: "SASL_SSL"      # Opcionalis
    sasl_mechanism: "PLAIN"
  topics:
    workflow_events: "aiflow.workflow.events"
    workflow_results: "aiflow.workflow.results"
    dlq: "aiflow.dlq"
```

---

## 2. Kafka Integracio Reszletesen

### 2.1 Event-Driven Workflow Triggerek

```python
# Scheduler konfiguracio
class EventTrigger(BaseModel):
    name: str
    workflow_name: str
    source: Literal["redis", "kafka", "rabbitmq"]
    topic: str
    group_id: str
    filter_expression: str | None = None   # JMESPath szuro
    transform_expression: str | None = None  # JMESPath transzformacio

# Pelda: Szamla erkezett -> invoice_processing workflow indul
EventTrigger(
    name="on-invoice-received",
    workflow_name="invoice-processing",
    source="kafka",
    topic="documents.invoices.received",
    group_id="aiflow-invoice-consumer",
    filter_expression="type == 'invoice' && status == 'new'",
    transform_expression="{document_url: url, metadata: metadata}",
)
```

### 2.2 Workflow Eredmenyek Publikalasa

```python
# Automatikusan publikaija a workflow eredmenyet Kafka-ba
# Minden WorkflowRun vegeredmenye -> aiflow.workflow.results topic

# Kafka message:
{
    "event": "workflow.completed",
    "workflow_name": "invoice-processing",
    "run_id": "abc-123",
    "status": "completed",
    "output_data": {...},
    "cost_usd": 0.058,
    "duration_ms": 12340,
    "team_id": "finance",
    "timestamp": "2026-03-27T10:15:30Z"
}
```

### 2.3 Schema Registry Integracio

```python
# Workflow input/output Pydantic modellek exportalasa Avro schema-kent
# aiflow schema export --workflow invoice-processing --format avro

# Bejovo uzenet: deszeializalo a schema registry-bol
# Kimeno uzenet: szerializalo a schema registry-be

class KafkaMessageBroker(MessageBroker):
    def __init__(self, bootstrap_servers, schema_registry_url=None):
        self._producer = AIOKafkaProducer(bootstrap_servers=bootstrap_servers)
        if schema_registry_url:
            self._schema_registry = SchemaRegistryClient({"url": schema_registry_url})
            self._serializer = AvroSerializer(self._schema_registry)
```

### 2.4 Back-Pressure es Flow Control

```
Kafka Consumer
    |
    +-- Rate limiter (max N message/sec)
    |
    +-- Queue depth check:
    |     |-- arq queue < threshold -> folytat
    |     |-- arq queue >= threshold -> consumer.pause()
    |     |-- arq queue < threshold/2 -> consumer.resume()
    |
    +-- arq job queue
    |
    +-- Worker pool (K8s HPA skalazza queue depth alapjan)
```

---

## 3. Integracio Mas Middleware-rel

### 3.1 RabbitMQ

```yaml
messaging:
  broker: rabbitmq
  rabbitmq:
    url: "amqp://user:pass@rabbitmq:5672/"
    exchange: "aiflow"
    exchange_type: "topic"
```

### 3.2 Azure Service Bus

```yaml
messaging:
  broker: azure_servicebus
  azure_servicebus:
    connection_string: "${AZURE_SERVICEBUS_CONNECTION_STRING}"
    namespace: "aiflow-prod"
```

### 3.3 AWS SQS

```yaml
messaging:
  broker: aws_sqs
  aws_sqs:
    region: "eu-central-1"
    queue_prefix: "aiflow-"
```

### 3.4 Redis Streams (Default)

Nulla konfiguracio - a meglevo Redis infrastruktura hasznalata:

```yaml
messaging:
  broker: redis_streams  # Default
  # Nincs extra konfiguracio - a meglevo AIFLOW_REDIS_URL-t hasznalja
```

---

## 4. Integracio Tipikus Vallalati Rendszerekkel

### 4.1 SAP Integracio Pelda

```python
# Skill: sap_document_processing
@workflow(name="sap-invoice-import")
def sap_invoice(wf: WorkflowBuilder):
    wf.step(receive_from_kafka)     # Kafka topic: sap.documents.outbound
    wf.step(classify_document)       # AI: szamla tipus felismeres
    wf.step(extract_data)            # AI: szamla adatok kinyerese
    wf.step(validate_against_sap)    # SAP RFC/OData hivas validaciora
    wf.step(post_to_sap)            # SAP posting
    wf.step(publish_result)          # Kafka topic: aiflow.results.sap
```

### 4.2 Email Integracio Pelda

```python
@workflow(name="email-classification-routing")
def email_routing(wf: WorkflowBuilder):
    wf.step(receive_email)           # Webhook: email service
    wf.step(classify_intent)          # AI: szandek felismeres
    wf.branch(
        on="classify_intent",
        when={
            "output.category == 'complaint'": ["escalate_to_support"],
            "output.category == 'invoice'": ["forward_to_finance"],
            "output.category == 'request'": ["create_ticket"],
        },
        otherwise="archive",
    )
```

### 4.3 REST API Webhook Integracio

```python
# Barmelyik kulso rendszer webhook-kal triggerelheti a workflow-t

# Scheduler konfiguracio:
ScheduleDefinition(
    name="external-erp-webhook",
    workflow_name="process-erp-document",
    trigger_type=TriggerType.WEBHOOK,
    webhook_path="/hooks/erp-document",  # POST /hooks/erp-document
)

# Automatikusan regisztralt FastAPI route:
# POST /hooks/erp-document -> enqueue workflow -> 202 Accepted
```

---

## 5. Konyvtar Struktura Bovites

```
src/aiflow/contrib/messaging/
    __init__.py
    base.py                 # MessageBroker abstract (ha kulon fajlba kell)
    redis_streams.py        # Redis Streams adapter (default)
    kafka.py                # Apache Kafka adapter
    rabbitmq.py             # RabbitMQ adapter
    azure_servicebus.py     # Azure Service Bus adapter
    aws_sqs.py              # AWS SQS adapter
```

**Uj fuggosegek (opcionalis):**

```toml
[project.optional-dependencies]
kafka = ["aiokafka>=0.10", "confluent-kafka[avro,schemaregistry]>=2.3"]
rabbitmq = ["aio-pika>=9.3"]
azure = ["azure-servicebus>=7.11"]
aws = ["aiobotocore>=2.9"]
```

Telepites skill igeny szerint:
```bash
pip install aiflow[kafka]    # Kafka adapter-rel
pip install aiflow[rabbitmq] # RabbitMQ adapter-rel
```
