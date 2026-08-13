from order_asset_pipeline import AssetUploadRequest, OrderAssetPipeline


class RecordedStorage:
    def __init__(self, found: bool) -> None:
        self.found = found
        self.presign_args: tuple[object, object, object] | None = None

    def storage_bucket_create(self, name: str) -> dict[str, object]:
        return {"name": name}

    def storage_object_presign(self, bucket: str, key: str, **body: object) -> dict[str, object]:
        self.presign_args = (bucket, key, body)
        return {"url": "https://upload.example/signed"}

    def storage_object_head(self, bucket: str, key: str) -> dict[str, object]:
        return {"found": self.found}


def request() -> AssetUploadRequest:
    return AssetUploadRequest(
        order_id="ord-1042",
        product_id="sku-poster-7",
        filename="print-ready.pdf",
        content_type="application/pdf",
        max_bytes=8_000_000,
        customer_email="buyer@example.com",
    )


def test_uploaded_asset_releases_order_and_builds_receipt() -> None:
    storage = RecordedStorage(found=True)
    pipeline = OrderAssetPipeline(storage, "commerce-order-assets")

    ticket = pipeline.begin_checkout_upload(request())
    result = pipeline.plan_fulfillment(request(), ticket)

    assert ticket.method == "PUT"
    assert result.status == "ready_for_fulfillment"
    assert result.receipt == {
        "order_id": "ord-1042",
        "asset_key": "orders/ord-1042/products/sku-poster-7/print-ready.pdf",
        "line_status": "asset_received",
    }


def test_missing_asset_keeps_order_out_of_fulfillment() -> None:
    storage = RecordedStorage(found=False)
    pipeline = OrderAssetPipeline(storage, "commerce-order-assets")

    ticket = pipeline.begin_checkout_upload(request())
    result = pipeline.plan_fulfillment(request(), ticket)

    assert result.status == "awaiting_asset"
    assert result.receipt is None
