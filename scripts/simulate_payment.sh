#!/usr/bin/env bash
# Simulate a fake Razorpay payment event to Redpanda
# Triggers the Finance Workflow via event ingestion

set -euo pipefail

# Configuration
REDPANDA_BROKER="${REDPANDA_BROKERS:-localhost:19092}"
TOPIC="${KAFKA_TOPIC:-payment-events}"
TENANT_ID="${TENANT_ID:-demo-tenant}"

# Generate fake payment event
VENDOR="${VENDOR:-aws}"
AMOUNT="${AMOUNT:-15000.00}"
CURRENCY="${CURRENCY:-INR}"
EVENT_TYPE="${EVENT_TYPE:-payment.success}"

# Create JSON payload
PAYLOAD=$(cat <<EOF
{
  "event_type": "${EVENT_TYPE}",
  "tenant_id": "${TENANT_ID}",
  "vendor": "${VENDOR}",
  "amount": ${AMOUNT},
  "currency": "${CURRENCY}",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "payment_id": "pay_$(date +%s)",
  "description": "Simulated payment for testing"
}
EOF
)

echo "📤 Publishing payment event to Redpanda..."
echo "   Broker: ${REDPANDA_BROKER}"
echo "   Topic: ${TOPIC}"
echo "   Payload: ${PAYLOAD}"

# Publish to Redpanda using kafka-console-producer
# Note: Using docker exec to access the Redpanda container
docker exec -i iterateswarm-redpanda /bin/sh -c "
  echo '${PAYLOAD}' | /usr/bin/rpk topic produce '${TOPIC}'
" 2>/dev/null || {
  # Fallback: use Python with kafka-python if rpk not available
  echo "   (Using Python fallback...)"
  python3 -c "
from kafka import KafkaProducer
import json

producer = KafkaProducer(
    bootstrap_servers='${REDPANDA_BROKER}',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

payload = json.loads('${PAYLOAD}')
future = producer.send('${TOPIC}', value=payload)
record_metadata = future.get(timeout=10)
print(f'✓ Published to topic {record_metadata.topic} partition {record_metadata.partition} offset {record_metadata.offset}')
producer.close()
"
}

echo ""
echo "✓ Event published successfully"
echo "  Check Temporal UI at http://localhost:8088 for workflow execution"
