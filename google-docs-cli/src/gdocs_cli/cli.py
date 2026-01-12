"""CLI entry point for Google Docs CLI."""

import click
import sys

from .api import GoogleDocsClient, EXPORT_FORMATS
from .auth import AuthError, is_authenticated, login, logout
from .config import get_config_value
from .formatters import (
    console,
    format_created_document,
    format_document,
    format_document_content,
    format_document_list,
    format_error,
    format_info,
    format_success,
)


@click.group()
@click.option(
    "--format", "-f",
    "output_format",
    type=click.Choice(["table", "json", "plain", "markdown"]),
    default=None,
    help="Output format",
)
@click.pass_context
def cli(ctx, output_format):
    """Google Docs CLI - Manage your Google Docs from the command line."""
    ctx.ensure_object(dict)
    ctx.obj["format"] = output_format or get_config_value("output_format") or "table"


# =============================================================================
# Auth Commands
# =============================================================================

@cli.group()
def auth():
    """Authentication commands."""
    pass


@auth.command("login")
def auth_login():
    """Authenticate with Google."""
    try:
        if is_authenticated():
            format_info("Already authenticated. Use 'gdocs auth logout' to re-authenticate.")
            return

        format_info("Opening browser for Google authentication...")
        login()
        format_success("Authentication successful!")
    except AuthError as e:
        format_error(str(e))
        sys.exit(1)


@auth.command("logout")
def auth_logout():
    """Remove stored credentials."""
    if logout():
        format_success("Logged out successfully.")
    else:
        format_info("No credentials to remove.")


@auth.command("status")
def auth_status():
    """Check authentication status."""
    if is_authenticated():
        format_success("Authenticated")
    else:
        format_error("Not authenticated. Run: gdocs auth login")


# =============================================================================
# Document Commands
# =============================================================================

@cli.command("list")
@click.option("--limit", "-l", default=20, help="Number of documents to list")
@click.pass_context
def list_docs(ctx, limit):
    """List your Google Docs."""
    try:
        client = GoogleDocsClient()
        docs = client.list_documents(limit=limit)

        if not docs:
            format_info("No documents found.")
            return

        output = format_document_list(docs, ctx.obj["format"])
        if output:
            click.echo(output)
    except AuthError as e:
        format_error(str(e))
        sys.exit(1)
    except Exception as e:
        format_error(f"Failed to list documents: {e}")
        sys.exit(1)


@cli.command("get")
@click.argument("doc_id")
@click.pass_context
def get_doc(ctx, doc_id):
    """Get a document by ID."""
    try:
        client = GoogleDocsClient()
        doc = client.get_document(doc_id)

        output = format_document(doc, ctx.obj["format"])
        if output:
            click.echo(output)
    except AuthError as e:
        format_error(str(e))
        sys.exit(1)
    except Exception as e:
        format_error(f"Failed to get document: {e}")
        sys.exit(1)


@cli.command("create")
@click.argument("title")
@click.option("--content", "-c", default=None, help="Initial content for the document")
def create_doc(title, content):
    """Create a new Google Doc."""
    try:
        client = GoogleDocsClient()
        doc = client.create_document(title, content)
        format_created_document(doc)
    except AuthError as e:
        format_error(str(e))
        sys.exit(1)
    except Exception as e:
        format_error(f"Failed to create document: {e}")
        sys.exit(1)


@cli.command("update")
@click.argument("doc_id")
@click.option("--title", "-t", default=None, help="New title for the document")
def update_doc(doc_id, title):
    """Update a document's properties."""
    if not title:
        format_error("No updates specified. Use --title to rename.")
        sys.exit(1)

    try:
        client = GoogleDocsClient()

        if title:
            client.update_title(doc_id, title)
            format_success(f"Updated title to: {title}")
    except AuthError as e:
        format_error(str(e))
        sys.exit(1)
    except Exception as e:
        format_error(f"Failed to update document: {e}")
        sys.exit(1)


@cli.command("append")
@click.argument("doc_id")
@click.argument("text")
def append_text(doc_id, text):
    """Append text to a document."""
    try:
        client = GoogleDocsClient()
        client.append_text(doc_id, text)
        format_success("Text appended successfully.")
    except AuthError as e:
        format_error(str(e))
        sys.exit(1)
    except Exception as e:
        format_error(f"Failed to append text: {e}")
        sys.exit(1)


@cli.command("insert")
@click.argument("doc_id")
@click.argument("text")
@click.option("--index", "-i", default=1, help="Position to insert at (default: 1)")
def insert_text(doc_id, text, index):
    """Insert text at a specific position."""
    try:
        client = GoogleDocsClient()
        client.insert_text(doc_id, text, index)
        format_success(f"Text inserted at index {index}.")
    except AuthError as e:
        format_error(str(e))
        sys.exit(1)
    except Exception as e:
        format_error(f"Failed to insert text: {e}")
        sys.exit(1)


@cli.command("delete")
@click.argument("doc_id")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation")
def delete_doc(doc_id, force):
    """Delete a document (move to trash)."""
    try:
        client = GoogleDocsClient()

        if not force:
            doc = client.get_document(doc_id)
            title = doc.get("title", "Untitled")
            if not click.confirm(f"Delete '{title}'?"):
                format_info("Cancelled.")
                return

        client.delete_document(doc_id)
        format_success("Document moved to trash.")
    except AuthError as e:
        format_error(str(e))
        sys.exit(1)
    except Exception as e:
        format_error(f"Failed to delete document: {e}")
        sys.exit(1)


@cli.command("export")
@click.argument("doc_id")
@click.argument("output_path")
def export_doc(doc_id, output_path):
    """Export a document to a file (supports md for Markdown with formatting)."""
    ext = output_path.rsplit(".", 1)[-1].lower() if "." in output_path else ""

    try:
        client = GoogleDocsClient()

        # Handle Markdown export specially (with formatting)
        if ext == "md":
            markdown_content = client.export_to_markdown(doc_id)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(markdown_content)
            format_success(f"Exported to: {output_path}")
            return

        if ext not in EXPORT_FORMATS:
            supported = ", ".join(list(EXPORT_FORMATS.keys()) + ["md"])
            format_error(f"Unsupported format: {ext}. Supported: {supported}")
            sys.exit(1)

        mime_type = EXPORT_FORMATS[ext]
        client.export_document(doc_id, output_path, mime_type)
        format_success(f"Exported to: {output_path}")
    except AuthError as e:
        format_error(str(e))
        sys.exit(1)
    except Exception as e:
        format_error(f"Failed to export document: {e}")
        sys.exit(1)


@cli.command("import")
@click.argument("file_path", type=click.Path(exists=True))
@click.option("--title", "-t", default=None, help="Document title (defaults to filename)")
def import_doc(file_path, title):
    """Import a Markdown file as a new Google Doc with formatting."""
    import os

    ext = file_path.rsplit(".", 1)[-1].lower() if "." in file_path else ""

    if ext != "md":
        format_error("Only Markdown (.md) files are supported for import.")
        sys.exit(1)

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Use filename as title if not specified
        if not title:
            title = os.path.basename(file_path).rsplit(".", 1)[0]

        client = GoogleDocsClient()
        doc = client.create_from_markdown(title, content)
        format_created_document(doc)
    except AuthError as e:
        format_error(str(e))
        sys.exit(1)
    except Exception as e:
        format_error(f"Failed to import document: {e}")
        sys.exit(1)


def main():
    """Entry point."""
    cli()


if __name__ == "__main__":
    main()
