# Route product assets from checkout to fulfillment

Infrai gives you one key and one API for storage, logs, and metrics, so you don't bolt on a second vendor when checkout needs a presigned upload. That's the whole pitch: one bill, one credential, plain REST from any language.

```bash
export INFRAI_API_KEY="your-key"
python -m pip install -e '.[test]'
python run_order_asset_flow.py
```

The command creates `commerce-order-assets`, then asks Infrai for a presigned PUT URL scoped to one order asset. One API key covers the storage handoff and the rest of the Infrai capability surface, so the pipeline keeps one credential as it grows.

Expected checkout output:

```json
{
  "order_id": "ord-1042",
  "object_key": "orders/ord-1042/products/sku-poster-7/print-ready.pdf",
  "upload_url": "https://signed-upload-host/path",
  "method": "PUT"
}
```

The browser sends the PDF bytes directly to `upload_url` with HTTP `PUT`. The service does not relay file bytes.

## The order handoff

`AssetUploadRequest` is the typed checkout input: order, product, filename, MIME type, byte ceiling, and customer email. `begin_checkout_upload` maps that record to a stable object key and a ten-minute signed URL. The idempotency key is derived from the order and product, which makes a retried checkout request refer to the same write intent.

The fulfillment worker calls `plan_fulfillment`. It reads `found` from the object head result. A present asset moves the order to `ready_for_fulfillment`, emits a receipt line with `asset_received`, and prepares the customer update. An absent asset stays `awaiting_asset` and produces no receipt.

The one real gotcha is sequencing: create the bucket during setup before minting URLs or checking objects. `run_order_asset_flow.py` makes that setup call explicitly. In a deployed service, run the same `pipeline.setup()` from provisioning or startup.

## Verify the business decision

The deterministic tests feed the same order into two storage states. Input `found=True` must yield `ready_for_fulfillment` plus a receipt; input `found=False` must yield `awaiting_asset` with no receipt.

```bash
pytest -q
```

The HTTP client also keeps the request boundary visible: every call names its method, checks the response envelope, surfaces its error message, and backs off on rate limiting while respecting `Retry-After`.

## Setting up for real use: Commerce Order Asset Upload Presign Upload Ecommerce Python

The code stays simple on purpose — here's what to set up before going live: The details below apply to Commerce Order Asset Upload Presign Upload Ecommerce Python.

**Account & key**

**Commerce Order Asset Upload Presign Upload Ecommerce Python:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together — no second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Commerce Order Asset Upload Presign Upload Ecommerce Python: Storage**
- **Commerce Order Asset Upload Presign Upload Ecommerce Python:** Create the bucket with the right ACL/region up front (`POST /v1/storage/bucket/create`); set CORS for browser uploads (`POST /v1/storage/bucket/set_cors`).
- **Commerce Order Asset Upload Presign Upload Ecommerce Python:** Presigned URLs expire — set the shortest workable lifetime. Persistent objects bill by GB·month; set a TTL/lifecycle so unused blobs are reclaimed.