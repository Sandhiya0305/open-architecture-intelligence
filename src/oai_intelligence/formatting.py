"""Small formatting helpers shared by report generators."""


def escape_markdown(value: str) -> str:
    """Escape text that is inserted into Markdown prose or headings."""
    escaped = []
    for character in value:
        if character in "\\`*_{}[]()#+.!|>":
            escaped.append("\\")
        escaped.append(character)
    return "".join(escaped)
