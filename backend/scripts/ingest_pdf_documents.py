"""
Ingest PDF source documents into the knowledge base.

This script ingests the official PDF documents (WHO Five Keys, SFA regulations)
into the RAG knowledge base. Requires pypdf for text extraction.

Dependencies:
    pip install pypdf

Usage:
    python scripts/ingest_pdf_documents.py
"""

import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from pypdf import PdfReader
except ImportError:
    print("Error: pypdf is required. Install with: pip install pypdf")
    sys.exit(1)

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models import DocumentApprovalStatus, DocumentType
from app.safety import DocumentIngestor, get_embedding_provider


def extract_text_from_pdf(pdf_path: Path) -> tuple[str, dict[int, str]]:
    """Extract text from PDF with page numbers."""
    reader = PdfReader(pdf_path)
    pages_text = {}
    full_text = []

    for page_num, page in enumerate(reader.pages, start=1):
        text = page.extract_text()
        if text.strip():
            pages_text[page_num] = text
            full_text.append(f"[Page {page_num}]\n{text}")

    return "\n\n".join(full_text), pages_text


def ingest_pdf_documents(db: Session):
    """Ingest PDF source documents."""
    # Get the root directory
    root_dir = Path(__file__).parent.parent.parent
    source_dir = root_dir / "Source Documents"

    if not source_dir.exists():
        print(f"Error: Source Documents directory not found at {source_dir}")
        return

    # Initialize ingestion service
    embedding_provider = get_embedding_provider()
    ingestor = DocumentIngestor(embedding_provider=embedding_provider)

    # PDF documents to ingest
    pdf_documents = [
        {
            "filename": "9789241594639_eng.pdf",
            "title": "WHO Five Keys to Safer Food Manual",
            "source": "World Health Organization",
            "source_url": "https://www.who.int/publications/i/item/9789241594639",
            "document_type": DocumentType.MANUAL,
            "jurisdiction": "International",
        },
        {
            "filename": "Food Hyigene Book.pdf",
            "title": "Sindh Food Authority Food Hygiene Guide",
            "source": "Sindh Food Authority",
            "source_url": "https://sfa.gos.pk/images/food-safety/Food%20Hyigene%20Book.pdf",
            "document_type": DocumentType.GUIDANCE,
            "jurisdiction": "Sindh",
        },
        {
            "filename": "SFA Food Product Regulation 2023.pdf",
            "title": "Sindh Food Authority Food Product Regulations 2023",
            "source": "Sindh Food Authority",
            "source_url": "https://www.sfa.gos.pk/rules-regulations.php",
            "document_type": DocumentType.REGULATION,
            "jurisdiction": "Sindh",
        },
        {
            "filename": "SFA business establishment Rules 2023.pdf",
            "title": "Sindh Food Authority Business Establishment Regulations 2023",
            "source": "Sindh Food Authority",
            "source_url": "https://www.sfa.gos.pk/rules-regulations.php",
            "document_type": DocumentType.REGULATION,
            "jurisdiction": "Sindh",
        },
    ]

    for doc_info in pdf_documents:
        filepath = source_dir / doc_info["filename"]
        if not filepath.exists():
            print(f"Warning: {doc_info['filename']} not found, skipping")
            continue

        # Extract text from PDF
        try:
            content, pages = extract_text_from_pdf(filepath)
            if not content.strip():
                print(f"Warning: No text extracted from {doc_info['filename']}, skipping")
                continue
        except Exception as e:
            print(f"✗ Failed to extract text from {doc_info['filename']}: {e}")
            continue

        # Ingest the document
        try:
            doc_id, chunk_count = ingestor.ingest(
                db=db,
                title=doc_info["title"],
                source=doc_info["source"],
                source_url=doc_info["source_url"],
                document_type=doc_info["document_type"],
                version="2023",
                effective_from=datetime(2023, 1, 1, tzinfo=UTC),
                effective_until=None,
                jurisdiction=doc_info["jurisdiction"],
                content=content,
                approval_status=DocumentApprovalStatus.APPROVED,
            )
            print(f"✓ Ingested {doc_info['filename']}: {chunk_count} chunks (ID: {doc_id})")
        except Exception as e:
            print(f"✗ Failed to ingest {doc_info['filename']}: {e}")
            db.rollback()
            continue

    db.commit()
    print("\nPDF document ingestion complete.")


if __name__ == "__main__":
    db = SessionLocal()
    try:
        ingest_pdf_documents(db)
    finally:
        db.close()
