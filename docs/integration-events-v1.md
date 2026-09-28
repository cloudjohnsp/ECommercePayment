# Contrato de webhook de pagamento v1

O gateway envia webhooks assinados usando o mesmo envelope versionado dos
eventos do ecossistema. As propriedades do envelope são camelCase e obrigatórias:

```json
{
  "messageId": "14ec2d2d-df09-5a91-ad5f-7719e1d75c47",
  "eventType": "payment.approved",
  "version": "1",
  "occurredAt": "2026-09-27T12:00:00+00:00",
  "correlationId": "checkout-123",
  "payload": {
    "id": "pay_example",
    "reference": "11111111-1111-1111-1111-111111111111",
    "amount": "99.90",
    "currency": "BRL",
    "status": "approved"
  }
}
```

`eventType` pode ser `payment.approved`, `payment.declined` ou
`payment.refunded`. `messageId` é determinístico para pagamento e transição.
O corpo canônico completo é assinado em `X-Payment-Signature`, e o mesmo
`correlationId` é enviado em `X-Correlation-ID`.

O schema v1 é imutável. Campos novos compatíveis são opcionais e devem ser
ignorados por consumers antigos. Mudanças incompatíveis exigem uma nova versão,
período explícito de convivência e retirada documentada da versão anterior.
