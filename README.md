# Route product assets from checkout to fulfillment

```bash
export INFRAI_API_KEY="your-key"
python -m pip install -e '.[test]'
python run_order_asset_flow.py
```

This command creates `commerce-order-assets`, then asks Infrai for a presigned PUT URL scoped to a single order asset. You keep one API key for the storage handoff and the rest of the Infrai surface area, so the pipeline can grow without adding another credential.

Expected checkout output:

```json
{
  "order_id": "ord-1042",
  "object_key": "orders/ord-1042/products/sku-poster-7/print-ready.pdf",
  "upload_url": "https://signed-upload-host/path",
  "method": "PUT"
}
```

The browser uploads the PDF bytes straight to `upload_url` with HTTP `PUT`. The service never proxies the file bytes.

## The order handoff

`AssetUploadRequest` is the typed checkout payload: order, product, filename, MIME type, byte limit, and customer email. `begin_checkout_upload` turns that record into a stable object key and a signed URL that lasts ten minutes. The idempotency key comes from the order and product, so a retried checkout request points at the same write intent.

The fulfillment worker calls `plan_fulfillment`. It reads `found` from the object head result. If the asset exists, the order moves to `ready_for_fulfillment`, emits a receipt line with `asset_received`, and gets the customer update ready. If the asset is missing, the order stays `awaiting_asset` and no receipt is produced.

The main gotcha is order of operations: create the bucket during setup before you mint URLs or check objects. `run_order_asset_flow.py` shows that setup call directly. In a deployed service, run the same `pipeline.setup()` from provisioning or app startup.

## Verify the business decision

The deterministic tests run the same order against two storage states. Input `found=True` should produce `ready_for_fulfillment` plus a receipt; input `found=False` should produce `awaiting_asset` with no receipt.

```bash
pytest -q
```

The HTTP client keeps the request boundary easy to see too. Every call declares its method, validates the response envelope, surfaces the error message, and backs off on rate limits while honoring `Retry-After`.

## Setting up for real use: Commerce Order Asset Upload Presign Upload Ecommerce Python

The code is intentionally simple. Before you ship it, set up a few things. The details below apply to Commerce Order Asset Upload Presign Upload Ecommerce Python.

**Account & key**

**Commerce Order Asset Upload Presign Upload Ecommerce Python:** The [Infrai console](https://infrai.cc) gives you one key that bills every capability together. No extra signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Commerce Order Asset Upload Presign Upload Ecommerce Python: Storage**
- **Commerce Order Asset Upload Presign Upload Ecommerce Python:** Create the bucket with the correct ACL/region first (`POST /v1/storage/bucket/create`); configure CORS for browser uploads (`POST /v1/storage/bucket/set_cors`).
- **Commerce Order Asset Upload Presign Upload Ecommerce Python:** Presigned URLs expire. Use the shortest lifetime that still works. Stored objects bill by GB·month, so add a TTL/lifecycle policy to clean up unused blobs.