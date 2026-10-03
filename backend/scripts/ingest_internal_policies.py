"""
Ingest KhaanaShare internal policy documents into the knowledge base.

This script loads the internal policy markdown files and ingests them
into the RAG knowledge base. Run this after database migration 0004.

Usage:
    python scripts/ingest_internal_policies.py
"""

import os
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models import DocumentApprovalStatus, DocumentType
from app.safety import DocumentIngestor, get_embedding_provider


def ingest_internal_policies(db: Session):
    """Ingest all internal policy documents."""
    # Get the root directory
    root_dir = Path(__file__).parent.parent.parent
    policies_dir = root_dir / "docs" / "knowledge" / "internal"

    if not policies_dir.exists():
        print(f"Error: Policies directory not found at {policies_dir}")
        return

    # Initialize ingestion service
    embedding_provider = get_embedding_provider()
    ingestor = DocumentIngestor(embedding_provider=embedding_provider)

    # Policy files to ingest
    policy_files = [
        "khaana_food_listing_policy.md",
        "khaana_provider_safety_checklist.md",
        "khaana_recipient_handling_policy.md",
        "khaana_pickup_handover_policy.md",
        "khaana_incident_escalation_policy.md",
        "khaana_ai_safety_policy.md",
    ]

    for filename in policy_files:
        filepath = policies_dir / filename
        if not filepath.exists():
            print(f"Warning: {filename} not found, skipping")
            continue

        # Read the file
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        # Extract title from first line
        lines = content.split("\n")
        title = lines[0].replace("#", "").strip() if lines else filename.replace(".md", "").replace("_", " ").title()

        # Ingest the document
        try:
            doc_id, chunk_count = ingestor.ingest(
                db=db,
                title=title,
                source="KhaanaShare Internal Policy",
                source_url=None,
                document_type=DocumentType.POLICY,
                version="1.0",
                effective_from=datetime(2026, 1, 1, tzinfo=UTC),
                effective_until=None,
                jurisdiction="Pakistan",
                content=content,
                approval_status=DocumentApprovalStatus.APPROVED,
            )
            print(f"✓ Ingested {filename}: {chunk_count} chunks (ID: {doc_id})")
        except Exception as e:
            print(f"✗ Failed to ingest {filename}: {e}")
            db.rollback()
            continue

    db.commit()
    print("\nInternal policy ingestion complete.")


if __name__ == "__main__":
    db = SessionLocal()
    try:
        ingest_internal_policies(db)
    finally:
        db.close()
