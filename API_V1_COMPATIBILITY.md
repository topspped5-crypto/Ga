# Payment Gateway API v1 compatibility

Base URL: your deployed service URL (set `base_url` in Admin Settings if needed).

The compatibility adapter adds the API shape described in the supplied payment-gateway documentation while keeping the existing Paytm and FamPay payment-verification modules intact.

## Authentication

Use either `X-API-Key: YOUR_GATEWAY_KEY` or `Authorization: Bearer YOUR_GATEWAY_KEY`. Query `api_key` is supported only for the legacy GET endpoints. Keep keys and webhook secrets on your server; never put them in browser JavaScript.

## Create payment

`POST /api/v1/payment/create`

```json
{"amount":99,"order_id":"ORDER10001","gateway":"paytm"}
```

`gateway` must explicitly be `paytm` or `fampay`. The API key must belong to an active gateway of the selected type. Amount is INR 1–100000. Repeating the same `order_id` for the same gateway returns the existing order.

Response includes `success`, `order_id`, `pay_id`, `status`, `amount`, `currency`, `gateway`, `transaction_id`, `payment_url`, `qr_url`, `qr_png_url`, `upi_uri`, `expires_at`, and `webhook_secret`. For FamPay, always display and collect the exact returned `amount` because its paise adjustment distinguishes pending payments.

## Status and verify

- `GET /api/v1/payment/status/{order_id}`
- `POST /api/v1/payment/verify` with `{"order_id":"ORDER10001"}`

Only `SUCCESS` means paid. Deliver only after verified success and amount match.

## Legacy GET aliases

- `GET /api/create_order.php?amount=99&order_id=ORDER10001&gateway=paytm&api_key=YOUR_GATEWAY_KEY`
- `GET /api/verify.php?order_id=ORDER10001&api_key=YOUR_GATEWAY_KEY`

## Webhook

Pass `webhook_url` when creating the payment. Headers:

- `X-Payment-Gateway-Timestamp`: Unix seconds
- `X-Payment-Gateway-Signature`: `sha256=HEX`

Signature is HMAC-SHA256 using the returned `webhook_secret` over `timestamp + "." + rawBody`. Reject timestamps older than five minutes, compare signatures in constant time, and deduplicate by `event_id`.

## Keepalive / Render

`/health` returns JSON health status. On Render, the app best-effort pings `RENDER_EXTERNAL_URL + /health` every four minutes when `RENDER_EXTERNAL_URL` is available. Optionally set `KEEPALIVE_URL` to an explicit public `/health` URL and `KEEPALIVE_INTERVAL=240`. This does not guarantee that Render Free will stay awake; an external uptime monitor or paid always-on service is required for dependable availability.

Existing `/api/v1/orders` routes and the Paytm/FamPay verification modules remain in place.
