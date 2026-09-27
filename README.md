# ECommerce Payment Gateway

Simulador de gateway de pagamento desenvolvido em Flask e PostgreSQL para integração com a ECommerce API.

## Executar com Docker

```bash
copy .env.example .env
# Preencha POSTGRES_PASSWORD e WEBHOOK_SECRET no arquivo .env.
docker compose up --build
```

A API ficará disponível em `http://localhost:5002` e o PostgreSQL em `localhost:5433`.
O Compose interrompe a inicialização quando a senha do PostgreSQL ou o segredo
compartilhado do webhook estiverem ausentes. Use o mesmo `WEBHOOK_SECRET` em
`PaymentGateway:WebhookSecret` na ECommerce API. O `.env` é local e ignorado
pelo Git.

`GET /health` retorna `200` somente quando o processo consegue consultar o
PostgreSQL. Quando o banco está indisponível, responde `503`; o healthcheck do
container e o readiness da ECommerce API usam esse resultado.

Valores monetários aceitam no máximo duas casas decimais e devem caber em
`Numeric(18,2)` (`9999999999999999.99` no máximo).
`reference` deve ser uma string não vazia de até 100 caracteres, `currency`
aceita exatamente três letras ASCII e `callbackUrl`, quando informado, deve ser
uma URL HTTP ou HTTPS absoluta. Motivos de recusa e reembolso são strings
opcionais de até 500 caracteres.

## Endpoints

### Saúde

```http
GET /health
```

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

### Reembolsar

Somente pagamentos aprovados podem ser reembolsados. A operação é idempotente:
repetir a chamada não envia outro webhook.

```http
POST /payments/{externalPaymentId}/refund
Content-Type: application/json

{"reason": "customer_request"}
```

O simulador envia um webhook para `callbackUrl` com o evento
`payment.approved`, `payment.declined` ou `payment.refunded`. A assinatura
HMAC-SHA256 fica no header `X-Payment-Signature`.

## Desenvolvimento local

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
# Preencha POSTGRES_PASSWORD e WEBHOOK_SECRET no arquivo .env.
flask --app wsgi db upgrade
flask --app wsgi run --port 5002
```

O extra `dotenv` do Flask carrega o `.env` nesses comandos. A aplicação falha
rapidamente quando a conexão do banco, `WEBHOOK_SECRET` ou um timeout positivo
não estiverem configurados, sem recorrer a credenciais fixas no código. Uma
`DATABASE_URL` explícita continua sendo aceita e tem precedência sobre os campos
`DATABASE_*`; os campos separados preservam corretamente senhas com caracteres
especiais.

## Testes

```bash
pytest
```
