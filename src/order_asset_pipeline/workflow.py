"""Order asset state transitions from checkout to fulfillment."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol


class StoragePort(Protocol):
    def storage_bucket_create(self, name: str) -> dict[str, object]:
        raise AssertionError

    def storage_object_presign(
        self,
        bucket: str,
        key: str,
        *,
        content_type: str,
        max_bytes: int,
        idempotency_key: str,
    ) -> dict[str, object]:
        raise AssertionError

    def storage_object_head(self, bucket: str, key: str) -> dict[str, object]:
        raise AssertionError


@dataclass(frozen=True)
class AssetUploadRequest:
    order_id: str
    product_id: str
    filename: str
    content_type: str
    max_bytes: int
    customer_email: str


@dataclass(frozen=True)
class UploadTicket:
    order_id: str
    object_key: str
    upload_url: str
    method: Literal["PUT"] = "PUT"


@dataclass(frozen=True)
class FulfillmentResult:
    order_id: str
    status: Literal["awaiting_asset", "ready_for_fulfillment"]
    receipt: dict[str, str] | None
    customer_update: dict[str, str]


class OrderAssetPipeline:
    def __init__(self, storage: StoragePort, bucket: str) -> None:
        self.storage = storage
        self.bucket = bucket

    def setup(self) -> None:
        self.storage.storage_bucket_create(self.bucket)

    def begin_checkout_upload(self, request: AssetUploadRequest) -> UploadTicket:
        key = f"orders/{request.order_id}/products/{request.product_id}/{request.filename}"
        signed = self.storage.storage_object_presign(
            self.bucket,
            key,
            content_type=request.content_type,
            max_bytes=request.max_bytes,
            idempotency_key=f"asset-upload-{request.order_id}-{request.product_id}",
        )
        url = signed.get("url")
        if not isinstance(url, str):
            raise ValueError("presign response did not contain a URL")
        return UploadTicket(request.order_id, key, url)

    def plan_fulfillment(
        self, request: AssetUploadRequest, ticket: UploadTicket
    ) -> FulfillmentResult:
        asset = self.storage.storage_object_head(self.bucket, ticket.object_key)
        if not asset.get("found"):
            return FulfillmentResult(
                order_id=request.order_id,
                status="awaiting_asset",
                receipt=None,
                customer_update={
                    "email": request.customer_email,
                    "message": "Your order is waiting for its product asset upload.",
                },
            )

        return FulfillmentResult(
            order_id=request.order_id,
            status="ready_for_fulfillment",
            receipt={
                "order_id": request.order_id,
                "asset_key": ticket.object_key,
                "line_status": "asset_received",
            },
            customer_update={
                "email": request.customer_email,
                "message": "Your product asset was received and fulfillment can begin.",
            },
        )
