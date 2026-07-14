from decimal import Decimal
from io import BytesIO
from typing import Optional

from django.utils import timezone

from lounge.models import MemberProfile, Receipt


def create_receipt(
    *,
    customer: Optional[MemberProfile],
    transaction_type: str,
    amount: Decimal,
    source_model: str,
    source_id: int,
) -> Receipt:
    receipt, _ = Receipt.objects.get_or_create(
        source_model=source_model,
        source_id=source_id,
        transaction_type=transaction_type,
        defaults={"customer": customer, "amount": amount},
    )
    return receipt


def build_receipt_pdf(receipt: Receipt) -> bytes:
    lines = [
        "E3 Lounge Receipt",
        f"Receipt Number: {receipt.receipt_number}",
        f"Date: {timezone.localtime(receipt.created_at):%d %b %Y, %I:%M %p}",
        f"Customer: {receipt.customer.member_id if receipt.customer else 'Walk-in'}",
        f"Transaction Type: {receipt.get_transaction_type_display()}",
        f"Amount: Rs {receipt.amount}",
    ]
    return _simple_pdf(lines)


def _simple_pdf(lines: list[str]) -> bytes:
    stream = "BT\n/F1 18 Tf\n72 760 Td\n"
    for index, line in enumerate(lines):
        escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        font_size = 18 if index == 0 else 12
        if index > 0:
            stream += f"/F1 {font_size} Tf\n0 -28 Td\n"
        stream += f"({escaped}) Tj\n"
    stream += "ET"
    stream_bytes = stream.encode("latin-1", errors="replace")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream_bytes)).encode("ascii") + b" >>\nstream\n" + stream_bytes + b"\nendstream",
    ]
    output = BytesIO()
    output.write(b"%PDF-1.4\n")
    offsets = [0]
    for number, body in enumerate(objects, start=1):
        offsets.append(output.tell())
        output.write(f"{number} 0 obj\n".encode("ascii"))
        output.write(body)
        output.write(b"\nendobj\n")
    xref = output.tell()
    output.write(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    output.write(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.write(f"{offset:010d} 00000 n \n".encode("ascii"))
    output.write(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode("ascii"))
    return output.getvalue()
