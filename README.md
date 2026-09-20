# ECommerce Payment Gateway

Simulador de gateway de pagamento desenvolvido em Flask e PostgreSQL para integração com a ECommerce API.

## Executar com Docker

```bash
docker compose up --build
```

A API ficará disponível em `http://localhost:5002` e o PostgreSQL em `localhost:5433`.

## Endpoints

### Criar pagamento

```http
POST /payments
Idempotency-Key: order-123
Content-Type: application/json

{
  "amount": 299.90,
  "currency": "BRL",
  "reference": "order-123",
  "callbackUrl": "http://host.docker.internal:5000/api/webhooks/payments"
}
```

### Consultar pagamento

```http
GET /payments/{externalPaymentId}
```

### Aprovar ou recusar

```http
POST /payments/{externalPaymentId}/approve
POST /payments/{externalPaymentId}/decline

{"reason": "card_declined"}
```

O simulador envia um webhook para `callbackUrl` com o evento `payment.approved` ou `payment.declined`. A assinatura HMAC-SHA256 fica no header `X-Payment-Signature`.

## Desenvolvimento local

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
flask --app wsgi db upgrade
flask --app wsgi run --port 5002
```

## Testes

```bash
pytest
```
