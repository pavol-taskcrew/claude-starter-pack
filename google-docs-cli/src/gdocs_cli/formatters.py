"""Output formatters for Google Docs CLI."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

console = Console()


def format_document_list(docs: List[Dict[str, Any]], output_format: str = "table") -> str:
    """Format a list of documents."""
    if output_format == "json":
        return json.dumps(docs, indent=2, default=str)

    if output_format == "plain":
        lines = []
        for doc in docs:
            lines.append(f"{doc['id']}\t{doc['name']}")
        return "\n".join(lines)

    # Table format (default)
    table = Table(title="Google Docs")
    table.add_column("ID", style="dim")
    table.add_column("Name", style="bold")
    table.add_column("Modified", style="cyan")

    for doc in docs:
        modified = _format_date(doc.get("modifiedTime", ""))
        table.add_row(doc["id"], doc["name"], modified)

    console.print(table)
    return ""


def format_document(doc: Dict[str, Any], output_format: str = "table") -> str:
    """Format a single document."""
    if output_format == "json":
        return json.dumps(doc, indent=2, default=str)

    if output_format == "plain":
        text = _extract_text_from_doc(doc)
        return f"Title: {doc.get('title', 'Untitled')}\n\n{text}"

    # Table format (rich panel)
    title = doc.get("title", "Untitled")
    doc_id = doc.get("documentId", "Unknown")
    text = _extract_text_from_doc(doc)

    console.print(Panel(
        text.strip() or "[dim]Empty document[/dim]",
        title=f"[bold]{title}[/bold]",
        subtitle=f"[dim]{doc_id}[/dim]",
    ))
    return ""


def format_document_content(doc: Dict[str, Any], output_format: str = "table") -> str:
    """Format document content (text only)."""
    if output_format == "json":
        return json.dumps(doc, indent=2, default=str)

    text = _extract_text_from_doc(doc)

    if output_format == "plain":
        return text

    if output_format == "markdown":
        return _convert_to_markdown(doc)

    # Default: just print the text
    return text


def format_success(message: str) -> None:
    """Print a success message."""
    console.print(f"[green]✓[/green] {message}")


def format_error(message: str) -> None:
    """Print an error message."""
    console.print(f"[red]✗[/red] {message}")


def format_info(message: str) -> None:
    """Print an info message."""
    console.print(f"[blue]ℹ[/blue] {message}")


def format_created_document(doc: Dict[str, Any]) -> None:
    """Format output for a newly created document."""
    doc_id = doc.get("documentId", "Unknown")
    title = doc.get("title", "Untitled")
    url = f"https://docs.google.com/document/d/{doc_id}/edit"

    console.print(f"[green]✓[/green] Created document: [bold]{title}[/bold]")
    console.print(f"  ID:  {doc_id}")
    console.print(f"  URL: [link={url}]{url}[/link]")


def _format_date(date_str: str) -> str:
    """Format an ISO date string to human-readable format."""
    if not date_str:
        return ""
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M")
    except (ValueError, AttributeError):
        return date_str


def _extract_text_from_doc(doc: Dict[str, Any]) -> str:
    """Extract plain text from document body."""
    text_parts = []
    content = doc.get("body", {}).get("content", [])

    for element in content:
        if "paragraph" in element:
            for para_element in element["paragraph"].get("elements", []):
                if "textRun" in para_element:
                    text_parts.append(para_element["textRun"].get("content", ""))

    return "".join(text_parts)


def _convert_to_markdown(doc: Dict[str, Any]) -> str:
    """Convert document to basic Markdown."""
    lines = []
    content = doc.get("body", {}).get("content", [])

    for element in content:
        if "paragraph" not in element:
            continue

        paragraph = element["paragraph"]
        style = paragraph.get("paragraphStyle", {}).get("namedStyleType", "NORMAL_TEXT")

        para_text = ""
        for para_element in paragraph.get("elements", []):
            if "textRun" in para_element:
                text = para_element["textRun"].get("content", "")
                text_style = para_element["textRun"].get("textStyle", {})

                if text_style.get("bold"):
                    text = f"**{text.strip()}**"
                if text_style.get("italic"):
                    text = f"*{text.strip()}*"

                para_text += text

        # Apply heading styles
        if style == "HEADING_1":
            para_text = f"# {para_text.strip()}"
        elif style == "HEADING_2":
            para_text = f"## {para_text.strip()}"
        elif style == "HEADING_3":
            para_text = f"### {para_text.strip()}"
        elif style == "HEADING_4":
            para_text = f"#### {para_text.strip()}"
        elif style == "HEADING_5":
            para_text = f"##### {para_text.strip()}"
        elif style == "HEADING_6":
            para_text = f"###### {para_text.strip()}"

        lines.append(para_text)

    return "".join(lines)
