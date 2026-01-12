"""Google Docs and Drive API wrapper."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2.credentials import Credentials
import io

from .auth import require_auth
from .markdown import parse_markdown_phased, doc_to_markdown


class GoogleDocsClient:
    """Client for interacting with Google Docs and Drive APIs."""

    def __init__(self, creds: Optional[Credentials] = None):
        """Initialize the client with credentials."""
        self.creds = creds or require_auth()
        self._docs_service = None
        self._drive_service = None

    @property
    def docs(self):
        """Get Google Docs service."""
        if self._docs_service is None:
            self._docs_service = build("docs", "v1", credentials=self.creds)
        return self._docs_service

    @property
    def drive(self):
        """Get Google Drive service."""
        if self._drive_service is None:
            self._drive_service = build("drive", "v3", credentials=self.creds)
        return self._drive_service

    def list_documents(self, limit: int = 20) -> List[Dict[str, Any]]:
        """List Google Docs documents."""
        results = (
            self.drive.files()
            .list(
                q="mimeType='application/vnd.google-apps.document'",
                pageSize=limit,
                fields="files(id, name, modifiedTime, createdTime)",
                orderBy="modifiedTime desc",
            )
            .execute()
        )
        return results.get("files", [])

    def get_document(self, doc_id: str) -> Dict[str, Any]:
        """Get a document by ID."""
        return self.docs.documents().get(documentId=doc_id).execute()

    def get_document_text(self, doc_id: str) -> str:
        """Get plain text content of a document."""
        doc = self.get_document(doc_id)
        return _extract_text(doc)

    def create_document(self, title: str, content: Optional[str] = None) -> Dict[str, Any]:
        """Create a new document."""
        doc = self.docs.documents().create(body={"title": title}).execute()
        doc_id = doc["documentId"]

        if content:
            self.append_text(doc_id, content)
            doc = self.get_document(doc_id)

        return doc

    def update_title(self, doc_id: str, new_title: str) -> None:
        """Update document title via Drive API."""
        self.drive.files().update(fileId=doc_id, body={"name": new_title}).execute()

    def append_text(self, doc_id: str, text: str) -> Dict[str, Any]:
        """Append text to the end of a document."""
        doc = self.get_document(doc_id)
        end_index = doc["body"]["content"][-1]["endIndex"] - 1

        requests = [
            {
                "insertText": {
                    "location": {"index": end_index},
                    "text": text,
                }
            }
        ]

        return (
            self.docs.documents()
            .batchUpdate(documentId=doc_id, body={"requests": requests})
            .execute()
        )

    def insert_text(self, doc_id: str, text: str, index: int = 1) -> Dict[str, Any]:
        """Insert text at a specific index."""
        requests = [
            {
                "insertText": {
                    "location": {"index": index},
                    "text": text,
                }
            }
        ]

        return (
            self.docs.documents()
            .batchUpdate(documentId=doc_id, body={"requests": requests})
            .execute()
        )

    def delete_document(self, doc_id: str) -> None:
        """Move document to trash."""
        self.drive.files().update(fileId=doc_id, body={"trashed": True}).execute()

    def create_from_markdown(self, title: str, markdown_content: str) -> Dict[str, Any]:
        """Create a new document from Markdown content with formatting."""
        doc = self.docs.documents().create(body={"title": title}).execute()
        doc_id = doc["documentId"]

        # Parse markdown into phases (regular content vs tables)
        phases = parse_markdown_phased(markdown_content)

        for phase in phases:
            if phase["type"] == "requests":
                # Regular content - just execute the requests
                if phase["requests"]:
                    self.docs.documents().batchUpdate(
                        documentId=doc_id,
                        body={"requests": phase["requests"]}
                    ).execute()
            elif phase["type"] == "table":
                # Table - need to get current document state first
                current_doc = self.get_document(doc_id)
                end_index = current_doc["body"]["content"][-1]["endIndex"] - 1

                # Build table requests at current end position
                table_requests = self._build_table_requests(
                    phase["headers"],
                    phase["rows"],
                    end_index
                )
                if table_requests:
                    self.docs.documents().batchUpdate(
                        documentId=doc_id,
                        body={"requests": table_requests}
                    ).execute()

        return self.get_document(doc_id)

    def _build_table_requests(
        self,
        headers: List[str],
        rows: List[List[str]],
        start_index: int
    ) -> List[Dict[str, Any]]:
        """Build requests for a native Google Docs table."""
        requests = []
        num_cols = len(headers)
        num_rows = 1 + len(rows)  # header + data rows

        # Step 1: Insert the table structure
        requests.append({
            "insertTable": {
                "rows": num_rows,
                "columns": num_cols,
                "location": {"index": start_index}
            }
        })

        # Step 2: Build all cells with their content
        all_cells = []

        # Header row (row 0)
        for col, text in enumerate(headers):
            all_cells.append({"row": 0, "col": col, "text": text, "is_header": True})

        # Data rows (rows 1+)
        for row_idx, row_data in enumerate(rows):
            for col in range(num_cols):
                text = row_data[col] if col < len(row_data) else ""
                all_cells.append({"row": row_idx + 1, "col": col, "text": text, "is_header": False})

        # Step 3: Insert cell content in REVERSE order to avoid index shifting
        # Cell index formula: start_index + 4 + row * (1 + num_cols * 2) + col * 2
        for cell in reversed(all_cells):
            row = cell["row"]
            col = cell["col"]
            text = cell["text"]
            is_header = cell["is_header"]

            if not text:
                continue

            cell_index = start_index + 4 + row * (1 + num_cols * 2) + col * 2

            # Insert text
            requests.append({
                "insertText": {
                    "location": {"index": cell_index},
                    "text": text
                }
            })

            # Bold header cells
            if is_header:
                requests.append({
                    "updateTextStyle": {
                        "range": {
                            "startIndex": cell_index,
                            "endIndex": cell_index + len(text)
                        },
                        "textStyle": {"bold": True},
                        "fields": "bold"
                    }
                })

        return requests

    def export_to_markdown(self, doc_id: str) -> str:
        """Export a document to Markdown format with formatting preserved."""
        doc = self.get_document(doc_id)
        return doc_to_markdown(doc)

    def export_document(self, doc_id: str, output_path: str, mime_type: str) -> None:
        """Export document to a file."""
        request = self.drive.files().export_media(fileId=doc_id, mimeType=mime_type)

        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)

        done = False
        while not done:
            _, done = downloader.next_chunk()

        with open(output_path, "wb") as f:
            f.write(fh.getvalue())


def _extract_text(doc: Dict[str, Any]) -> str:
    """Extract plain text from a document structure."""
    text_parts = []
    content = doc.get("body", {}).get("content", [])

    for element in content:
        if "paragraph" in element:
            for para_element in element["paragraph"].get("elements", []):
                if "textRun" in para_element:
                    text_parts.append(para_element["textRun"].get("content", ""))

    return "".join(text_parts)


# Export format mappings
EXPORT_FORMATS = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "txt": "text/plain",
    "html": "text/html",
    "rtf": "application/rtf",
    "odt": "application/vnd.oasis.opendocument.text",
    "epub": "application/epub+zip",
}
