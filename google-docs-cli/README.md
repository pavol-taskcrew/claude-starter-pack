# Google Docs CLI

A command-line interface for managing Google Docs.

## Setup

### 1. Install the CLI

```bash
pip install -e ~/.claude/google-docs-cli
```

### 2. Set up Google Cloud Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable these APIs:
   - Google Docs API
   - Google Drive API
4. Go to **APIs & Services > Credentials**
5. Click **Create Credentials > OAuth 2.0 Client ID**
6. Select **Desktop app** as the application type
7. Download the credentials file
8. Save it as `~/.claude/google-docs-cli/credentials/credentials.json`

### 3. Authenticate

```bash
gdocs auth login
```

This opens a browser for Google authentication. After authenticating, you're ready to use the CLI.

## Usage

### Authentication

```bash
gdocs auth login     # Authenticate with Google
gdocs auth status    # Check auth status
gdocs auth logout    # Remove stored credentials
```

### List Documents

```bash
gdocs list                # List recent documents
gdocs list --limit 50     # List more documents
gdocs list -f json        # Output as JSON
```

### Get Document

```bash
gdocs get <doc-id>              # Display document content
gdocs get <doc-id> -f json      # Get as JSON
gdocs get <doc-id> -f markdown  # Get as Markdown
gdocs get <doc-id> -f plain     # Get as plain text
```

### Create Document

```bash
gdocs create "My Document"                    # Create empty document
gdocs create "My Document" -c "Hello world"   # Create with content
```

### Update Document

```bash
gdocs update <doc-id> --title "New Title"   # Rename document
gdocs append <doc-id> "Text to add"         # Append text
gdocs insert <doc-id> "Text" --index 1      # Insert at position
```

### Delete Document

```bash
gdocs delete <doc-id>         # Delete with confirmation
gdocs delete <doc-id> -f      # Force delete (no confirmation)
```

### Export Document

```bash
gdocs export <doc-id> output.pdf    # Export as PDF
gdocs export <doc-id> output.docx   # Export as Word
gdocs export <doc-id> output.txt    # Export as plain text
gdocs export <doc-id> output.html   # Export as HTML
```

Supported formats: pdf, docx, txt, html, rtf, odt, epub

## Output Formats

Use `-f` or `--format` to change output format:

- `table` (default) - Rich formatted tables
- `json` - JSON output for scripting
- `plain` - Plain text output
- `markdown` - Markdown formatted output

## Examples

```bash
# List docs and get the first one
gdocs list
gdocs get 1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms

# Create a new doc and add content
gdocs create "Meeting Notes"
# (copy the ID from output)
gdocs append <doc-id> "Agenda:\n1. Project updates\n2. Action items"

# Export a doc to PDF
gdocs export <doc-id> meeting-notes.pdf
```
