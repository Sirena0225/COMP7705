# HK-Market-Sentinel Frontend API Contract v1.0 (DRAFT)

## Endpoint: POST /api/v1/analyze
### Request
```json
{
  "request_id": "uuid4",
  "stock_code": "00700.HK",
  "text": "string (max 2000 chars)",
  "language_hint": "zh|en|mixed|null",
  "timestamp": "ISO8601"
}