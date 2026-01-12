---
name: google-docs
description: Interact with Google Docs via CLI. Use when reading, creating, updating, or exporting Google Docs during work sessions.
---

# Google Docs CLI

Manage Google Docs directly from Claude using the `gdocs` CLI.

**Important:** Use `python3 -m gdocs_cli.cli` to invoke the CLI (the `gdocs` alias may not be in PATH).

## Instructions

### Reading Documents

To get document content for context or reference:

```bash
# List recent documents to find the one you need
python3 -m gdocs_cli.cli list

# Get document content (use markdown format for best readability)
python3 -m gdocs_cli.cli get <doc-id> -f markdown

# Get as plain text
python3 -m gdocs_cli.cli get <doc-id> -f plain

# Get as JSON (for structured processing)
python3 -m gdocs_cli.cli get <doc-id> -f json
```

### Creating Documents

```bash
# Create empty document
python3 -m gdocs_cli.cli create "Document Title"

# Create with initial content
python3 -m gdocs_cli.cli create "Document Title" -c "Initial content here"
```

### Updating Documents

```bash
# Rename a document
python3 -m gdocs_cli.cli update <doc-id> --title "New Title"

# Append text to the end
python3 -m gdocs_cli.cli append <doc-id> "Text to append"

# Insert text at a specific position
python3 -m gdocs_cli.cli insert <doc-id> "Text to insert" --index 1
```

### Exporting Documents

```bash
# Export to various formats
python3 -m gdocs_cli.cli export <doc-id> output.pdf    # PDF
python3 -m gdocs_cli.cli export <doc-id> output.docx   # Word
python3 -m gdocs_cli.cli export <doc-id> output.txt    # Plain text
python3 -m gdocs_cli.cli export <doc-id> output.md     # Markdown
python3 -m gdocs_cli.cli export <doc-id> output.html   # HTML
```

### Deleting Documents

```bash
python3 -m gdocs_cli.cli delete <doc-id>      # With confirmation prompt
python3 -m gdocs_cli.cli delete <doc-id> -f   # Force delete (no confirmation)
```

## Common Workflows

### Read a doc for context
1. `python3 -m gdocs_cli.cli list` to find the document
2. `python3 -m gdocs_cli.cli get <doc-id> -f markdown` to read content

### Create meeting notes
1. `python3 -m gdocs_cli.cli create "Meeting Notes - <date>"`
2. Use the returned doc-id to append content as needed

### Export for sharing
1. `python3 -m gdocs_cli.cli export <doc-id> <filename>.<format>`
2. Supported: pdf, docx, txt, html, rtf, odt, epub

## Notes

- Document IDs are long alphanumeric strings (e.g., `1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms`)
- Use `-f json` output when you need to parse results programmatically
- If auth issues occur, run `python3 -m gdocs_cli.cli auth status` to check, then `python3 -m gdocs_cli.cli auth login` if needed
