import re
from docx import Document
from typing import Dict, List, Optional

# Constants to avoid magic values
# ALIGN_CENTER corresponds to docx.enum.text.WD_ALIGN_PARAGRAPH.CENTER
ALIGN_CENTER = 1
TYPE_HEADING = "heading"
TYPE_PART = "part"
TYPE_PAGE = "page"
TYPE_MAIN = "main"

# Dictionary keys for block structure
KEY_TYPE = "type"
KEY_TEXT = "text"

# Precompiled patterns and prepared exception sets for performance/readability
EXCEPTIONS = (
    "༄༅།།",
    "༄༅༅།།",
)

PATTERN_FOUR = re.compile(r"(?:།\s*){4}")
PATTERN_TWO = re.compile(r"།\s*།")
PAGE_RE = re.compile(r"^(\d+)(.*)")


def add_br_tags(text: str) -> str:
    """
    Adds <br /> <p> after the symbols "།" followed by "།" (with any number of spaces between),
    as well as after 4 consecutive "།" (possibly with spaces).
    Does not add tags after exceptions defined in EXCEPTIONS.
    """
    # Check if text starts with an exception (possibly with leading spaces)
    text_stripped = text.lstrip()
    prefix_spaces = text[:len(text) - len(text_stripped)]
    
    for exception in EXCEPTIONS:
        if text_stripped.startswith(exception):
            # Text starts with exception - don't process this part
            exception_end = len(prefix_spaces) + len(exception)
            prefix = text[:exception_end]
            suffix = text[exception_end:]
            # Process only the suffix
            processed_suffix = _process_patterns(suffix)
            return prefix + processed_suffix
    
    # Text doesn't start with exception - process normally
    return _process_patterns(text)


def _process_patterns(text: str) -> str:
    """Process regex patterns to add tags, skipping exceptions."""
    def add_tag_after(match: re.Match) -> str:
        s = match.group(0)
        # Check if the matched string itself is an exception
        if s.replace(" ", "") in EXCEPTIONS:
            return s
        return f"{s}<br /> <p>"
    
    # Apply substitutions using precompiled regex patterns
    text = PATTERN_FOUR.sub(add_tag_after, text)
    text = PATTERN_TWO.sub(add_tag_after, text)
    return text


def get_alignment(para) -> int:
    """Get paragraph alignment, defaulting to 0 if None."""
    return para.alignment if para.alignment is not None else 0


def _is_centered(alignment: Optional[int]) -> bool:
    return alignment == ALIGN_CENTER


def parse_docx_to_blocks(input_path: str) -> List[Dict[str, str]]:
    doc = Document(input_path)
    blocks: List[Dict[str, str]] = []

    for idx, para in enumerate(doc.paragraphs):
        line = para.text.strip()
        alignment = get_alignment(para)

        if not line:
            continue

        # Heading: first non-part line at document start
        if idx == 0 and not _is_centered(alignment):
            blocks.append({KEY_TYPE: TYPE_HEADING, KEY_TEXT: line})
            continue

        # Part: centered alignment (no numbering yet)
        if _is_centered(alignment):
            blocks.append({KEY_TYPE: TYPE_PART, KEY_TEXT: line})
            continue

        # Page: line starts with number, not centered
        m = PAGE_RE.match(line)
        if m and not _is_centered(alignment):
            page_num, rest = m.group(1), m.group(2).lstrip()
            blocks.append({KEY_TYPE: TYPE_PAGE, KEY_TEXT: f"page {page_num}"})
            if rest:
                blocks.append({KEY_TYPE: TYPE_MAIN, KEY_TEXT: rest})
            continue

        # Main text: all else
        blocks.append({KEY_TYPE: TYPE_MAIN, KEY_TEXT: line})

    return blocks

def process_main_text_blocks(blocks: List[Dict[str, str]]) -> None:
    """Process main text blocks by adding <br /> and <p> tags after specific symbols."""
    for block in blocks:
        if block.get(KEY_TYPE) == TYPE_MAIN:
            text = block.get(KEY_TEXT, '')
            if text:
                block[KEY_TEXT] = add_br_tags(text)


def swap_part_page_blocks(blocks: List[Dict[str, str]]) -> None:
    """Swap adjacent part and page blocks so that page comes before part."""
    i = 1
    while i < len(blocks):
        if (blocks[i - 1].get(KEY_TYPE) == TYPE_PART and 
            blocks[i].get(KEY_TYPE) == TYPE_PAGE):
            blocks[i - 1], blocks[i] = blocks[i], blocks[i - 1]
            i += 2
        else:
            i += 1

def insert_new_part_after_page(blocks: List[Dict[str, str]]) -> None:
    """
    Insert a new part block after each page block if no part exists in the segment
    before the next page. Iterates backwards to keep insertion indices stable.
    """
    # Iterate backwards to keep insertion indices stable
    for i in reversed(range(len(blocks) - 1)):
        if (blocks[i].get(KEY_TYPE) == TYPE_PAGE and 
            blocks[i + 1].get(KEY_TYPE) == TYPE_MAIN):
            # Find next page boundary (exclusive)
            next_page_idx: Optional[int] = None
            for j in range(i + 1, len(blocks)):
                if blocks[j].get(KEY_TYPE) == TYPE_PAGE:
                    next_page_idx = j
                    break
            # Check if there's any part before next page (or end)
            next_page_idx = next_page_idx if next_page_idx is not None else len(blocks)
            segment = blocks[i + 1:next_page_idx]

            # Skip if segment is empty or already contains a part
            if not segment or any(b.get(KEY_TYPE) == TYPE_PART for b in segment):
                continue

            blocks.insert(i + 1, {KEY_TYPE: TYPE_PART, KEY_TEXT: ''})


def numerate_parts(blocks: List[Dict[str, str]]) -> None:
    """Number all part blocks sequentially as '## part1 ##', '## part2 ##', etc."""
    num = 1
    for block in blocks:
        if block.get(KEY_TYPE) == TYPE_PART:
            block[KEY_TEXT] = f"## part{num} ##"
            num += 1

def stringbuild_data(blocks: List[Dict[str, str]]) -> str:
    """
    Print only the 'text' field for all blocks except 'heading'.
    After each block of type 'page' or 'part' always add a newline.
    After 'main', add a newline only if the next block exists and is 'page' or 'part'.
    Never add a newline after 'main' if the next block is also 'main'.
    """
    result_data = []
    n = len(blocks)
    for i, block in enumerate(blocks):
        btype = block.get(KEY_TYPE)
        if btype == TYPE_HEADING:
            continue

        text = block.get(KEY_TEXT, '')
        if text:
            result_data.append(text)

        if btype in (TYPE_PAGE, TYPE_PART):
            result_data.append('\n')
        elif btype == TYPE_MAIN:
            next_type = blocks[i + 1].get(KEY_TYPE) if i + 1 < n else None
            if next_type in (TYPE_PAGE, TYPE_PART):
                result_data.append('\n')

    return "".join(result_data)

def convert(doc_file_path: str) -> str:
    """
    Convert a DOCX file to a Wikitext string.
    """
    blocks = parse_docx_to_blocks(doc_file_path)
    process_main_text_blocks(blocks)
    swap_part_page_blocks(blocks)
    insert_new_part_after_page(blocks)
    numerate_parts(blocks)
    result_text = stringbuild_data(blocks)
    return result_text