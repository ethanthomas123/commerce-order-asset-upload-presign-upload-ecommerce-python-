"""Mint an upload URL and print the checkout handoff."""

import json
import os

from order_asset_pipeline import AssetUploadRequest, OrderAssetPipeline
from order_asset_pipeline.infrai_client import InfraiClient


def main() -> None:
    client = InfraiClient(os.environ["INFRAI_API_KEY"])
    pipeline = OrderAssetPipeline(client, bucket="commerce-order-assets")
    request = AssetUploadRequest(
        order_id="ord-1042",
        product_id="sku-poster-7",
        filename="print-ready.pdf",
        content_type="application/pdf",
        max_bytes=8_000_000,
        customer_email="buyer@example.com",
    )
    ticket = pipeline.begin_checkout_upload(request)
    print(json.dumps(ticket.__dict__, indent=2))
    print("PUT the file bytes to upload_url, then run plan_fulfillment in your order worker.")


if __name__ == "__main__":
    main()
