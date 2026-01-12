"""Markdown parsing and conversion for Google Docs."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple


def parse_markdown_phased(content: str) -> List[Dict[str, Any]]:
    """
    Parse Markdown content into phases for Google Docs API.

    Returns a list of phases, where each phase is either:
    - {"type": "requests", "requests": [...]} for regular content
    - {"type": "table", "headers": [...], "rows": [[...], ...]} for tables

    Tables are separated into their own phases because they need to be
    inserted with knowledge of the current document state.
    """
    phases = []
    current_requests = []
    current_index = 1  # Google Docs starts at index 1

    lines = content.split('\n')
    i = 0

    while i < len(lines):
        line = lines[i]

        # Check for code blocks
        if line.startswith('```'):
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].startswith('```'):
                code_lines.append(lines[i])
                i += 1
            code_text = '\n'.join(code_lines) + '\n'
            if code_text.strip():
                current_requests.append(_insert_text_request(current_index, code_text))
                end_index = current_index + len(code_text)
                current_requests.append(_update_text_style_request(
                    current_index, end_index,
                    font_family="Courier New"
                ))
                current_requests.append(_update_paragraph_style_request_code_block(
                    current_index, end_index
                ))
                current_index = end_index
            i += 1
            continue

        # Check for horizontal rules
        if re.match(r'^(-{3,}|\*{3,}|_{3,})$', line.strip()):
            hr_text = "─" * 50 + '\n'
            current_requests.append(_insert_text_request(current_index, hr_text))
            end_index = current_index + len(hr_text) - 1
            current_requests.append(_update_text_style_request(
                current_index, end_index,
                foreground_color={"red": 0.7, "green": 0.7, "blue": 0.7}
            ))
            current_requests.append(_update_paragraph_style_request_alignment(
                current_index, end_index + 1, "CENTER"
            ))
            current_index += len(hr_text)
            i += 1
            continue

        # Check for tables (start of table)
        if '|' in line and re.match(r'^\|.*\|$', line.strip()):
            # Save current requests as a phase before the table
            if current_requests:
                phases.append({"type": "requests", "requests": current_requests})
                current_requests = []

            # Parse table
            table_lines = [line]
            i += 1
            while i < len(lines) and '|' in lines[i] and re.match(r'^\|.*\|$', lines[i].strip()):
                table_lines.append(lines[i])
                i += 1

            headers, rows = _parse_table_data(table_lines)
            phases.append({"type": "table", "headers": headers, "rows": rows})

            # Reset index to 1 - next phase will start fresh after querying doc
            current_index = 1
            continue

        # Check for headings
        heading_match = re.match(r'^(#{1,6})\s+(.+)$', line)
        if heading_match:
            level = len(heading_match.group(1))
            heading_content = heading_match.group(2)
            text, style_requests = _parse_inline_formatting(heading_content + '\n', current_index)
            current_requests.append(_insert_text_request(current_index, text))
            end_index = current_index + len(text)
            current_requests.append(_update_paragraph_style_request(
                current_index, end_index,
                f"HEADING_{level}"
            ))
            for req in style_requests:
                current_requests.append(req)
            current_index = end_index
            i += 1
            continue

        # Check for blockquotes
        blockquote_match = re.match(r'^>\s*(.*)$', line)
        if blockquote_match:
            quote_text = blockquote_match.group(1)
            text, style_requests = _parse_inline_formatting(quote_text + '\n', current_index)
            current_requests.append(_insert_text_request(current_index, text))
            end_index = current_index + len(text)
            current_requests.append(_update_paragraph_style_request_blockquote(
                current_index, end_index
            ))
            current_requests.append(_update_text_style_request(
                current_index, end_index - 1,
                italic=True,
                foreground_color={"red": 0.4, "green": 0.4, "blue": 0.4}
            ))
            current_requests.extend(style_requests)
            current_index = end_index
            i += 1
            continue

        # Check for task lists
        task_match = re.match(r'^[-\*]\s+\[([ xX])\]\s+(.+)$', line)
        if task_match:
            is_checked = task_match.group(1).lower() == 'x'
            task_text = task_match.group(2)
            checkbox = "☑ " if is_checked else "☐ "
            full_text = checkbox + task_text + '\n'
            text, style_requests = _parse_inline_formatting(full_text, current_index)
            current_requests.append(_insert_text_request(current_index, text))
            end_index = current_index + len(text)
            current_requests.append(_create_bullet_request(current_index, end_index))
            if is_checked:
                current_requests.append(_update_text_style_request(
                    current_index + 2, end_index - 1,
                    strikethrough=True,
                    foreground_color={"red": 0.6, "green": 0.6, "blue": 0.6}
                ))
            current_requests.extend(style_requests)
            current_index = end_index
            i += 1
            continue

        # Check for bullet lists
        bullet_match = re.match(r'^([\s]*)[-\*]\s+(.+)$', line)
        if bullet_match:
            indent_str = bullet_match.group(1)
            nesting_level = len(indent_str) // 2
            list_text = bullet_match.group(2)
            text, style_requests = _parse_inline_formatting(list_text + '\n', current_index)
            current_requests.append(_insert_text_request(current_index, text))
            end_index = current_index + len(text)
            current_requests.append(_create_bullet_request(current_index, end_index, nesting_level))
            current_requests.extend(style_requests)
            current_index = end_index
            i += 1
            continue

        # Check for numbered lists
        numbered_match = re.match(r'^([\s]*)\d+\.\s+(.+)$', line)
        if numbered_match:
            indent_str = numbered_match.group(1)
            nesting_level = len(indent_str) // 2
            list_text = numbered_match.group(2)
            text, style_requests = _parse_inline_formatting(list_text + '\n', current_index)
            current_requests.append(_insert_text_request(current_index, text))
            end_index = current_index + len(text)
            current_requests.append(_create_numbered_list_request(current_index, end_index, nesting_level))
            current_requests.extend(style_requests)
            current_index = end_index
            i += 1
            continue

        # Regular paragraph with inline formatting
        if line.strip():
            text, style_requests = _parse_inline_formatting(line + '\n', current_index)
            current_requests.append(_insert_text_request(current_index, text))
            current_requests.extend(style_requests)
            current_index += len(text)
        elif i < len(lines) - 1:
            current_requests.append(_insert_text_request(current_index, '\n'))
            current_index += 1

        i += 1

    # Add any remaining requests as final phase
    if current_requests:
        phases.append({"type": "requests", "requests": current_requests})

    return phases


def _parse_table_data(lines: List[str]) -> Tuple[List[str], List[List[str]]]:
    """Parse table lines into headers and rows."""
    # Parse header row
    header_row = lines[0]
    headers = [cell.strip() for cell in header_row.strip('|').split('|')]

    # Skip separator row (|---|---|)
    data_start = 1
    if len(lines) > 1 and re.match(r'^\|[\s\-:|]+\|$', lines[1]):
        data_start = 2

    # Parse data rows
    rows = []
    for line in lines[data_start:]:
        cells = [cell.strip() for cell in line.strip('|').split('|')]
        rows.append(cells)

    return headers, rows


def parse_markdown(content: str) -> List[Dict[str, Any]]:
    """
    Parse Markdown content into Google Docs API requests.

    Supports:
    - Headings (# to ######)
    - Bold (**text** or __text__)
    - Italic (*text* or _text_)
    - Strikethrough (~~text~~)
    - Underline (++text++)
    - Highlight (==text==)
    - Superscript (^text^)
    - Subscript (~text~ - single tilde with no spaces)
    - Bullet lists (- or *)
    - Numbered lists (1. 2. etc)
    - Task lists (- [ ] or - [x])
    - Links [text](url)
    - Code blocks (```code```)
    - Inline code (`code`)
    - Blockquotes (> text)
    - Horizontal rules (--- or ***)
    - Tables (| col | col |)
    """
    requests = []
    current_index = 1  # Google Docs starts at index 1

    lines = content.split('\n')
    i = 0

    while i < len(lines):
        line = lines[i]

        # Check for code blocks
        if line.startswith('```'):
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].startswith('```'):
                code_lines.append(lines[i])
                i += 1
            code_text = '\n'.join(code_lines) + '\n'
            if code_text.strip():
                requests.append(_insert_text_request(current_index, code_text))
                end_index = current_index + len(code_text)
                # Apply monospace font to text
                requests.append(_update_text_style_request(
                    current_index, end_index,
                    font_family="Courier New"
                ))
                # Apply paragraph-level shading for full-width background
                requests.append(_update_paragraph_style_request_code_block(
                    current_index, end_index
                ))
                current_index = end_index
            i += 1
            continue

        # Check for horizontal rules
        if re.match(r'^(-{3,}|\*{3,}|_{3,})$', line.strip()):
            # Insert a horizontal line using repeated dashes with styling
            hr_text = "─" * 50 + '\n'
            requests.append(_insert_text_request(current_index, hr_text))
            end_index = current_index + len(hr_text) - 1
            requests.append(_update_text_style_request(
                current_index, end_index,
                foreground_color={"red": 0.7, "green": 0.7, "blue": 0.7}
            ))
            requests.append(_update_paragraph_style_request_alignment(
                current_index, end_index + 1, "CENTER"
            ))
            current_index += len(hr_text)
            i += 1
            continue

        # Check for tables (start of table)
        if '|' in line and re.match(r'^\|.*\|$', line.strip()):
            table_lines = [line]
            i += 1
            while i < len(lines) and '|' in lines[i] and re.match(r'^\|.*\|$', lines[i].strip()):
                table_lines.append(lines[i])
                i += 1
            table_requests, new_index = _parse_table(table_lines, current_index)
            requests.extend(table_requests)
            current_index = new_index
            continue

        # Check for headings
        heading_match = re.match(r'^(#{1,6})\s+(.+)$', line)
        if heading_match:
            level = len(heading_match.group(1))
            heading_content = heading_match.group(2)
            text, style_requests = _parse_inline_formatting(heading_content + '\n', current_index)
            requests.append(_insert_text_request(current_index, text))
            end_index = current_index + len(text)
            requests.append(_update_paragraph_style_request(
                current_index, end_index,
                f"HEADING_{level}"
            ))
            # Apply inline styles with adjusted indices
            for req in style_requests:
                requests.append(req)
            current_index = end_index
            i += 1
            continue

        # Check for blockquotes
        blockquote_match = re.match(r'^>\s*(.*)$', line)
        if blockquote_match:
            quote_text = blockquote_match.group(1)
            text, style_requests = _parse_inline_formatting(quote_text + '\n', current_index)
            requests.append(_insert_text_request(current_index, text))
            end_index = current_index + len(text)
            # Style as blockquote with indentation and left border
            requests.append(_update_paragraph_style_request_blockquote(
                current_index, end_index
            ))
            requests.append(_update_text_style_request(
                current_index, end_index - 1,
                italic=True,
                foreground_color={"red": 0.4, "green": 0.4, "blue": 0.4}
            ))
            requests.extend(style_requests)
            current_index = end_index
            i += 1
            continue

        # Check for task lists
        task_match = re.match(r'^[-\*]\s+\[([ xX])\]\s+(.+)$', line)
        if task_match:
            is_checked = task_match.group(1).lower() == 'x'
            task_text = task_match.group(2)
            # Use checkbox characters
            checkbox = "☑ " if is_checked else "☐ "
            full_text = checkbox + task_text + '\n'
            text, style_requests = _parse_inline_formatting(full_text, current_index)
            requests.append(_insert_text_request(current_index, text))
            end_index = current_index + len(text)
            requests.append(_create_bullet_request(current_index, end_index))
            if is_checked:
                # Strike through completed tasks
                requests.append(_update_text_style_request(
                    current_index + 2, end_index - 1,
                    strikethrough=True,
                    foreground_color={"red": 0.6, "green": 0.6, "blue": 0.6}
                ))
            requests.extend(style_requests)
            current_index = end_index
            i += 1
            continue

        # Check for bullet lists (must come after task lists)
        bullet_match = re.match(r'^([\s]*)[-\*]\s+(.+)$', line)
        if bullet_match:
            indent_str = bullet_match.group(1)
            nesting_level = len(indent_str) // 2
            list_text = bullet_match.group(2)
            text, style_requests = _parse_inline_formatting(list_text + '\n', current_index)
            requests.append(_insert_text_request(current_index, text))
            end_index = current_index + len(text)
            requests.append(_create_bullet_request(current_index, end_index, nesting_level))
            requests.extend(style_requests)
            current_index = end_index
            i += 1
            continue

        # Check for numbered lists
        numbered_match = re.match(r'^([\s]*)\d+\.\s+(.+)$', line)
        if numbered_match:
            indent_str = numbered_match.group(1)
            nesting_level = len(indent_str) // 2
            list_text = numbered_match.group(2)
            text, style_requests = _parse_inline_formatting(list_text + '\n', current_index)
            requests.append(_insert_text_request(current_index, text))
            end_index = current_index + len(text)
            requests.append(_create_numbered_list_request(current_index, end_index, nesting_level))
            requests.extend(style_requests)
            current_index = end_index
            i += 1
            continue

        # Regular paragraph with inline formatting
        if line.strip():
            text, style_requests = _parse_inline_formatting(line + '\n', current_index)
            requests.append(_insert_text_request(current_index, text))
            requests.extend(style_requests)
            current_index += len(text)
        elif i < len(lines) - 1:  # Empty line (paragraph break)
            requests.append(_insert_text_request(current_index, '\n'))
            current_index += 1

        i += 1

    return requests


def _parse_inline_formatting(text: str, start_index: int) -> Tuple[str, List[Dict[str, Any]]]:
    """Parse inline formatting and return clean text with style requests."""
    style_requests = []
    result_text = ""
    current_pos = start_index
    i = 0

    while i < len(text):
        # Check for links [text](url)
        link_match = re.match(r'\[([^\]]+)\]\(([^)]+)\)', text[i:])
        if link_match:
            link_text = link_match.group(1)
            link_url = link_match.group(2)
            result_text += link_text
            style_requests.append(_update_text_style_request(
                current_pos, current_pos + len(link_text),
                link_url=link_url
            ))
            current_pos += len(link_text)
            i += len(link_match.group(0))
            continue

        # Check for strikethrough ~~text~~
        strike_match = re.match(r'~~(.+?)~~', text[i:])
        if strike_match:
            strike_text = strike_match.group(1)
            result_text += strike_text
            style_requests.append(_update_text_style_request(
                current_pos, current_pos + len(strike_text),
                strikethrough=True
            ))
            current_pos += len(strike_text)
            i += len(strike_match.group(0))
            continue

        # Check for highlight ==text==
        highlight_match = re.match(r'==(.+?)==', text[i:])
        if highlight_match:
            highlight_text = highlight_match.group(1)
            result_text += highlight_text
            style_requests.append(_update_text_style_request(
                current_pos, current_pos + len(highlight_text),
                background_color={"red": 1.0, "green": 1.0, "blue": 0.0}  # Yellow
            ))
            current_pos += len(highlight_text)
            i += len(highlight_match.group(0))
            continue

        # Check for underline ++text++
        underline_match = re.match(r'\+\+(.+?)\+\+', text[i:])
        if underline_match:
            underline_text = underline_match.group(1)
            result_text += underline_text
            style_requests.append(_update_text_style_request(
                current_pos, current_pos + len(underline_text),
                underline=True
            ))
            current_pos += len(underline_text)
            i += len(underline_match.group(0))
            continue

        # Check for superscript ^text^
        super_match = re.match(r'\^([^\^]+)\^', text[i:])
        if super_match:
            super_text = super_match.group(1)
            result_text += super_text
            style_requests.append(_update_text_style_request(
                current_pos, current_pos + len(super_text),
                baseline_offset="SUPERSCRIPT"
            ))
            current_pos += len(super_text)
            i += len(super_match.group(0))
            continue

        # Check for subscript ~text~ (single tilde, not ~~)
        sub_match = re.match(r'(?<!~)~([^~]+)~(?!~)', text[i:])
        if sub_match and not text[i:].startswith('~~'):
            sub_text = sub_match.group(1)
            result_text += sub_text
            style_requests.append(_update_text_style_request(
                current_pos, current_pos + len(sub_text),
                baseline_offset="SUBSCRIPT"
            ))
            current_pos += len(sub_text)
            i += len(sub_match.group(0))
            continue

        # Check for bold+italic ***text***
        bold_italic_match = re.match(r'\*\*\*(.+?)\*\*\*', text[i:])
        if bold_italic_match:
            bi_text = bold_italic_match.group(1)
            result_text += bi_text
            style_requests.append(_update_text_style_request(
                current_pos, current_pos + len(bi_text),
                bold=True,
                italic=True
            ))
            current_pos += len(bi_text)
            i += len(bold_italic_match.group(0))
            continue

        # Check for bold **text** or __text__
        bold_match = re.match(r'(\*\*|__)(.+?)\1', text[i:])
        if bold_match:
            bold_text = bold_match.group(2)
            result_text += bold_text
            style_requests.append(_update_text_style_request(
                current_pos, current_pos + len(bold_text),
                bold=True
            ))
            current_pos += len(bold_text)
            i += len(bold_match.group(0))
            continue

        # Check for italic *text* or _text_ (but not ** or __)
        if (text[i] == '*' or text[i] == '_') and not text[i:].startswith('**') and not text[i:].startswith('__'):
            italic_match = re.match(r'(\*|_)([^\*_]+)\1', text[i:])
            if italic_match:
                italic_text = italic_match.group(2)
                result_text += italic_text
                style_requests.append(_update_text_style_request(
                    current_pos, current_pos + len(italic_text),
                    italic=True
                ))
                current_pos += len(italic_text)
                i += len(italic_match.group(0))
                continue

        # Check for inline code `text`
        code_match = re.match(r'`([^`]+)`', text[i:])
        if code_match:
            code_text = code_match.group(1)
            result_text += code_text
            style_requests.append(_update_text_style_request(
                current_pos, current_pos + len(code_text),
                font_family="Courier New",
                background_color={"red": 0.95, "green": 0.95, "blue": 0.95}
            ))
            current_pos += len(code_text)
            i += len(code_match.group(0))
            continue

        # Regular character
        result_text += text[i]
        current_pos += 1
        i += 1

    return result_text, style_requests


def _parse_table(lines: List[str], start_index: int) -> Tuple[List[Dict[str, Any]], int]:
    """
    Parse a Markdown table and return requests.

    Uses a clean text-based table with box-drawing characters and monospace font.
    Native Google Docs tables require complex index management that breaks
    when mixed with other content in the same batch update.
    """
    requests = []
    current_index = start_index

    # Parse header row
    header_row = lines[0]
    headers = [cell.strip() for cell in header_row.strip('|').split('|')]
    num_cols = len(headers)

    # Skip separator row (|---|---|)
    data_start = 1
    if len(lines) > 1 and re.match(r'^\|[\s\-:|]+\|$', lines[1]):
        data_start = 2

    # Parse data rows
    data_rows = []
    for line in lines[data_start:]:
        cells = [cell.strip() for cell in line.strip('|').split('|')]
        # Ensure each row has the right number of columns
        while len(cells) < num_cols:
            cells.append("")
        data_rows.append(cells[:num_cols])

    # Calculate column widths (min 10 chars for readability)
    col_widths = [max(10, len(h)) for h in headers]
    for row in data_rows:
        for i, cell in enumerate(row):
            if i < len(col_widths):
                col_widths[i] = max(col_widths[i], len(cell))

    # Build table with box-drawing characters
    # Top border: ┌───────────┬───────────┐
    top_border = "┌" + "┬".join("─" * (w + 2) for w in col_widths) + "┐\n"
    requests.append(_insert_text_request(current_index, top_border))
    current_index += len(top_border)

    # Header row: │ Header1   │ Header2   │
    header_text = "│ " + " │ ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers)) + " │\n"
    header_start = current_index
    requests.append(_insert_text_request(current_index, header_text))
    current_index += len(header_text)

    # Header separator: ├───────────┼───────────┤
    header_sep = "├" + "┼".join("─" * (w + 2) for w in col_widths) + "┤\n"
    requests.append(_insert_text_request(current_index, header_sep))
    current_index += len(header_sep)

    # Data rows: │ Data1     │ Data2     │
    for row in data_rows:
        row_text = "│ " + " │ ".join(
            (row[i] if i < len(row) else "").ljust(col_widths[i])
            for i in range(len(col_widths))
        ) + " │\n"
        requests.append(_insert_text_request(current_index, row_text))
        current_index += len(row_text)

    # Bottom border: └───────────┴───────────┘
    bottom_border = "└" + "┴".join("─" * (w + 2) for w in col_widths) + "┘\n"
    requests.append(_insert_text_request(current_index, bottom_border))
    current_index += len(bottom_border)

    # Style the entire table with monospace font for alignment
    requests.append(_update_text_style_request(
        start_index, current_index,
        font_family="Courier New",
        font_size=10
    ))

    # Bold the header row text (between first │ and last │)
    requests.append(_update_text_style_request(
        header_start + 2, header_start + len(header_text) - 3,
        bold=True
    ))

    return requests, current_index


def _insert_text_request(index: int, text: str) -> Dict[str, Any]:
    """Create an insertText request."""
    return {
        "insertText": {
            "location": {"index": index},
            "text": text
        }
    }


def _update_text_style_request(
    start_index: int,
    end_index: int,
    bold: bool = None,
    italic: bool = None,
    underline: bool = None,
    strikethrough: bool = None,
    font_family: str = None,
    font_size: int = None,
    link_url: str = None,
    foreground_color: Dict[str, float] = None,
    background_color: Dict[str, float] = None,
    baseline_offset: str = None,
    small_caps: bool = None
) -> Dict[str, Any]:
    """Create an updateTextStyle request with all formatting options."""
    text_style = {}
    fields = []

    if bold is not None:
        text_style["bold"] = bold
        fields.append("bold")

    if italic is not None:
        text_style["italic"] = italic
        fields.append("italic")

    if underline is not None:
        text_style["underline"] = underline
        fields.append("underline")

    if strikethrough is not None:
        text_style["strikethrough"] = strikethrough
        fields.append("strikethrough")

    if font_family is not None:
        text_style["weightedFontFamily"] = {"fontFamily": font_family}
        fields.append("weightedFontFamily")

    if font_size is not None:
        text_style["fontSize"] = {"magnitude": font_size, "unit": "PT"}
        fields.append("fontSize")

    if link_url is not None:
        text_style["link"] = {"url": link_url}
        fields.append("link")

    if foreground_color is not None:
        text_style["foregroundColor"] = {"color": {"rgbColor": foreground_color}}
        fields.append("foregroundColor")

    if background_color is not None:
        text_style["backgroundColor"] = {"color": {"rgbColor": background_color}}
        fields.append("backgroundColor")

    if baseline_offset is not None:
        text_style["baselineOffset"] = baseline_offset
        fields.append("baselineOffset")

    if small_caps is not None:
        text_style["smallCaps"] = small_caps
        fields.append("smallCaps")

    return {
        "updateTextStyle": {
            "range": {
                "startIndex": start_index,
                "endIndex": end_index
            },
            "textStyle": text_style,
            "fields": ",".join(fields)
        }
    }


def _update_paragraph_style_request(
    start_index: int,
    end_index: int,
    named_style: str
) -> Dict[str, Any]:
    """Create an updateParagraphStyle request for headings."""
    return {
        "updateParagraphStyle": {
            "range": {
                "startIndex": start_index,
                "endIndex": end_index
            },
            "paragraphStyle": {
                "namedStyleType": named_style
            },
            "fields": "namedStyleType"
        }
    }


def _update_paragraph_style_request_alignment(
    start_index: int,
    end_index: int,
    alignment: str
) -> Dict[str, Any]:
    """Create an updateParagraphStyle request for alignment."""
    return {
        "updateParagraphStyle": {
            "range": {
                "startIndex": start_index,
                "endIndex": end_index
            },
            "paragraphStyle": {
                "alignment": alignment
            },
            "fields": "alignment"
        }
    }


def _update_paragraph_style_request_blockquote(
    start_index: int,
    end_index: int
) -> Dict[str, Any]:
    """Create an updateParagraphStyle request for blockquotes."""
    return {
        "updateParagraphStyle": {
            "range": {
                "startIndex": start_index,
                "endIndex": end_index
            },
            "paragraphStyle": {
                "indentStart": {"magnitude": 36, "unit": "PT"},
                "indentFirstLine": {"magnitude": 36, "unit": "PT"},
                "borderLeft": {
                    "color": {"color": {"rgbColor": {"red": 0.8, "green": 0.8, "blue": 0.8}}},
                    "width": {"magnitude": 3, "unit": "PT"},
                    "padding": {"magnitude": 12, "unit": "PT"},
                    "dashStyle": "SOLID"
                }
            },
            "fields": "indentStart,indentFirstLine,borderLeft"
        }
    }


def _update_paragraph_style_request_code_block(
    start_index: int,
    end_index: int
) -> Dict[str, Any]:
    """Create an updateParagraphStyle request for code blocks with full-width background."""
    return {
        "updateParagraphStyle": {
            "range": {
                "startIndex": start_index,
                "endIndex": end_index
            },
            "paragraphStyle": {
                "shading": {
                    "backgroundColor": {
                        "color": {
                            "rgbColor": {"red": 0.95, "green": 0.95, "blue": 0.95}
                        }
                    }
                },
                "indentStart": {"magnitude": 18, "unit": "PT"},
                "indentEnd": {"magnitude": 18, "unit": "PT"},
                "spaceAbove": {"magnitude": 6, "unit": "PT"},
                "spaceBelow": {"magnitude": 6, "unit": "PT"}
            },
            "fields": "shading,indentStart,indentEnd,spaceAbove,spaceBelow"
        }
    }


def _create_bullet_request(start_index: int, end_index: int, nesting_level: int = 0) -> Dict[str, Any]:
    """Create a bullet list request."""
    return {
        "createParagraphBullets": {
            "range": {
                "startIndex": start_index,
                "endIndex": end_index
            },
            "bulletPreset": "BULLET_DISC_CIRCLE_SQUARE"
        }
    }


def _create_numbered_list_request(start_index: int, end_index: int, nesting_level: int = 0) -> Dict[str, Any]:
    """Create a numbered list request."""
    return {
        "createParagraphBullets": {
            "range": {
                "startIndex": start_index,
                "endIndex": end_index
            },
            "bulletPreset": "NUMBERED_DECIMAL_NESTED"
        }
    }


def doc_to_markdown(doc: Dict[str, Any]) -> str:
    """
    Convert a Google Doc to Markdown format with full formatting.

    Handles:
    - Headings
    - Bold, italic, underline, strikethrough
    - Superscript and subscript
    - Highlight (background color)
    - Links
    - Bullet and numbered lists
    - Code formatting (monospace fonts)
    - Blockquotes (indented with border)
    """
    lines = []
    content = doc.get("body", {}).get("content", [])
    lists = doc.get("lists", {})

    for element in content:
        if "paragraph" not in element:
            continue

        paragraph = element["paragraph"]
        style = paragraph.get("paragraphStyle", {})
        named_style = style.get("namedStyleType", "NORMAL_TEXT")
        bullet = paragraph.get("bullet")

        # Check for blockquote (indented with left border)
        is_blockquote = False
        if style.get("borderLeft") and style.get("indentStart"):
            is_blockquote = True

        # Build paragraph text with inline formatting
        para_text = ""
        for para_element in paragraph.get("elements", []):
            if "textRun" not in para_element:
                continue

            text_run = para_element["textRun"]
            text = text_run.get("content", "")
            text_style = text_run.get("textStyle", {})

            # Skip if just a newline
            if text == "\n":
                continue

            # Strip trailing newline for processing
            text = text.rstrip("\n")

            # Apply formatting in order of precedence
            formatted_text = _format_text_run(text, text_style)
            para_text += formatted_text

        if not para_text:
            lines.append("")
            continue

        # Handle bullet/numbered lists
        if bullet:
            current_list_id = bullet.get("listId")
            nesting_level = bullet.get("nestingLevel", 0)
            indent = "  " * nesting_level

            list_props = lists.get(current_list_id, {}).get("listProperties", {})
            nesting_levels = list_props.get("nestingLevels", [{}])

            if nesting_level < len(nesting_levels):
                glyph_type = nesting_levels[nesting_level].get("glyphType", "")
            else:
                glyph_type = ""

            # Check for task list (checkbox characters)
            if para_text.startswith("☑ "):
                lines.append(f"{indent}- [x] {para_text[2:]}")
            elif para_text.startswith("☐ "):
                lines.append(f"{indent}- [ ] {para_text[2:]}")
            elif glyph_type in ["DECIMAL", "ALPHA", "ROMAN"]:
                lines.append(f"{indent}1. {para_text}")
            else:
                lines.append(f"{indent}- {para_text}")
            continue

        # Handle blockquotes
        if is_blockquote:
            lines.append(f"> {para_text}")
            continue

        # Handle headings
        if named_style.startswith("HEADING_"):
            level = int(named_style.split("_")[1])
            prefix = "#" * level
            lines.append(f"{prefix} {para_text}")
            continue

        # Check for horizontal rule (line of dashes)
        if para_text.strip() and all(c in "─-—" for c in para_text.strip()):
            lines.append("---")
            continue

        # Regular paragraph
        lines.append(para_text)

    return "\n".join(lines)


def _format_text_run(text: str, text_style: Dict[str, Any]) -> str:
    """Format a text run based on its style."""
    # Check for link first (exclusive)
    if "link" in text_style:
        url = text_style["link"].get("url", "")
        return f"[{text}]({url})"

    # Check for code (monospace font)
    font_family = text_style.get("weightedFontFamily", {}).get("fontFamily", "")
    is_code = "courier" in font_family.lower() or "mono" in font_family.lower()

    if is_code:
        return f"`{text}`"

    # Check for baseline offset (superscript/subscript)
    baseline = text_style.get("baselineOffset", "NONE")
    if baseline == "SUPERSCRIPT":
        return f"^{text}^"
    elif baseline == "SUBSCRIPT":
        return f"~{text}~"

    # Check for highlight (yellow background)
    bg_color = text_style.get("backgroundColor", {}).get("color", {}).get("rgbColor", {})
    if bg_color.get("red", 0) > 0.9 and bg_color.get("green", 0) > 0.9 and bg_color.get("blue", 0) < 0.2:
        text = f"=={text}=="

    # Apply text decorations
    is_bold = text_style.get("bold", False)
    is_italic = text_style.get("italic", False)
    is_underline = text_style.get("underline", False)
    is_strikethrough = text_style.get("strikethrough", False)

    if is_strikethrough:
        text = f"~~{text}~~"

    if is_underline:
        text = f"++{text}++"

    if is_bold and is_italic:
        text = f"***{text}***"
    elif is_bold:
        text = f"**{text}**"
    elif is_italic:
        text = f"*{text}*"

    return text
