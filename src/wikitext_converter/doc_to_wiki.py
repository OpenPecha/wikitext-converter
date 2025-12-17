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
    "༄༅། །",
    "༄༅༅། །",
)

PATTERN_FOUR = re.compile(r"(?:།\s*){4}")
PATTERN_TWO = re.compile(r"།\s*།")
PAGE_RE = re.compile(r"^(\d+)(.*)")


def add_br_tags(text: str) -> str:
    """
    Adds <br /> <p> after symbols "། །" and "།།" (with any number of spaces between),
    as well as after 4 consecutive "།" (possibly with spaces).
    Excludes exceptions: "༄༅།།", "༄༅༅།།", "༄༅། །", "༄༅༅། །".
    """
    # Check if text starts with an exception (possibly with leading spaces)
    text_stripped = text.lstrip()
    prefix_spaces = text[:len(text) - len(text_stripped)]
    
    # Normalize exceptions for comparison (remove spaces)
    exceptions_normalized = [exc.replace(" ", "") for exc in EXCEPTIONS]
    text_stripped_no_spaces = text_stripped.replace(" ", "")
    
    for i, exception_normalized in enumerate(exceptions_normalized):
        if text_stripped_no_spaces.startswith(exception_normalized):
            # Find the actual exception in text (with original spacing)
            exception = EXCEPTIONS[i]
            # Find where exception ends in original text
            # Need to account for spaces in exception
            exception_end = len(prefix_spaces)
            text_after_prefix = text[exception_end:]
            # Match exception accounting for variable spaces
            exception_pattern = exception.replace(" ", r"\s*")
            match = re.match(exception_pattern, text_after_prefix)
            if match:
                exception_end += match.end()
                prefix = text[:exception_end]
                suffix = text[exception_end:]
                # Process only the suffix
                processed_suffix = _process_patterns(suffix)
                return prefix + processed_suffix
    
    # Text doesn't start with exception - process normally
    return _process_patterns(text)


def _process_patterns(text: str) -> str:
    """
    Process regex patterns to add tags, skipping exceptions.
    Priority: PATTERN_FOUR (4 symbols) is processed first, then PATTERN_TWO (2 symbols).
    PATTERN_TWO does not process parts already handled by PATTERN_FOUR.
    """
    def check_exception(match: re.Match, original_text: str) -> bool:
        """Check if match is part of an exception."""
        s = match.group(0)
        start_pos = match.start()
        
        # Check if this match is part of an exception
        max_exception_len = max(len(exc) for exc in EXCEPTIONS)
        context_start = max(0, start_pos - max_exception_len)
        context = original_text[context_start:start_pos + len(s)]
        context_no_spaces = context.replace(" ", "")
        
        # Check if any exception appears in the context
        for exception_normalized in [exc.replace(" ", "") for exc in EXCEPTIONS]:
            if exception_normalized in context_no_spaces:
                # Check if match overlaps with exception
                exc_pos = context_no_spaces.find(exception_normalized)
                match_start_no_spaces = len(original_text[context_start:start_pos].replace(" ", ""))
                if exc_pos <= match_start_no_spaces < exc_pos + len(exception_normalized):
                    return True
        return False
    
    # First, process PATTERN_FOUR and record processed ranges in original text
    processed_ranges = []
    result_parts = []
    last_pos = 0
    
    for match in PATTERN_FOUR.finditer(text):
        # Add text before match
        result_parts.append(text[last_pos:match.start()])
        
        # Process match
        if check_exception(match, text):
            result_parts.append(match.group(0))
        else:
            result_parts.append(f"{match.group(0)}<br /> <p>")
            # Record processed range in original text
            processed_ranges.append((match.start(), match.end()))
        
        last_pos = match.end()
    
    # Add remaining text
    result_parts.append(text[last_pos:])
    text_after_four = "".join(result_parts)
    
    # Now process PATTERN_TWO, but skip matches that overlap with processed ranges
    # Find all PATTERN_TWO matches in original text
    two_matches = list(PATTERN_TWO.finditer(text))
    
    if not two_matches:
        return text_after_four
    
    # Process each PATTERN_TWO match, checking if it's in a processed range
    result_parts = []
    last_pos_in_result = 0
    
    for match in two_matches:
        start_pos = match.start()
        end_pos = match.end()
        
        # Check if this match overlaps with any processed range from PATTERN_FOUR
        in_processed_range = False
        for range_start, range_end in processed_ranges:
            if not (end_pos <= range_start or start_pos >= range_end):
                in_processed_range = True
                break
        
        if in_processed_range:
            continue  # Skip this match - already processed by PATTERN_FOUR
        
        # Find position in text_after_four (account for tags added by PATTERN_FOUR)
        tags_before = sum(1 for rs, re in processed_ranges if rs < start_pos)
        pos_in_result = start_pos + tags_before * 10
        
        # Add text before this match
        result_parts.append(text_after_four[last_pos_in_result:pos_in_result])
        
        # Process this match
        if check_exception(match, text):
            result_parts.append(match.group(0))
            last_pos_in_result = pos_in_result + len(match.group(0))
        else:
            result_parts.append(f"{match.group(0)}<br /> <p>")
            last_pos_in_result = pos_in_result + len(match.group(0)) + 10
    
    # Add remaining text
    result_parts.append(text_after_four[last_pos_in_result:])
    return "".join(result_parts)


def get_alignment(para) -> int:
    """Get paragraph alignment, defaulting to 0 if None."""
    return para.alignment if para.alignment is not None else 0


def _is_centered(alignment: Optional[int]) -> bool:
    return alignment == ALIGN_CENTER


def parse_docx_to_blocks(input_path: str) -> List[Dict[str, str]]:
    """
    Parse DOCX file into blocks according to structure:
    1. Heading: at document start, no part yet (part == 0), may contain page number
    2. Page: number at line start, not centered
    3. Part: centered alignment, may contain any text and numbers
    4. Main text: everything else
    """
    doc = Document(input_path)
    blocks: List[Dict[str, str]] = []
    part_count = 0  # Track number of parts encountered

    for idx, para in enumerate(doc.paragraphs):
        line = para.text.strip()
        alignment = get_alignment(para)

        if not line:
            continue

        # Part: centered alignment (can contain any text and numbers)
        if _is_centered(alignment):
            blocks.append({KEY_TYPE: TYPE_PART, KEY_TEXT: line})
            part_count += 1
            continue

        # Page: line starts with number, not centered
        m = PAGE_RE.match(line)
        if m and not _is_centered(alignment):
            page_num, rest = m.group(1), m.group(2).lstrip()
            blocks.append({KEY_TYPE: TYPE_PAGE, KEY_TEXT: f"page {page_num}"})
            if rest:
                blocks.append({KEY_TYPE: TYPE_MAIN, KEY_TEXT: rest})
            continue

        # Heading: at document start and no part encountered yet (part == 0)
        # May contain page number
        if idx == 0 and part_count == 0:
            blocks.append({KEY_TYPE: TYPE_HEADING, KEY_TEXT: line})
            continue

        # Main text: everything else
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
    Insert a new part block after page block if:
    - After page block there is a text block (MAIN)
    - AND there are parts on the current page (before next page)
    Then add a new part at the beginning of the page.
    Iterates backwards to keep insertion indices stable.
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

            # Skip if segment is empty
            if not segment:
                continue

            # If there ARE parts in the segment, add a new part at the beginning of the page
            if any(b.get(KEY_TYPE) == TYPE_PART for b in segment):
                blocks.insert(i + 1, {KEY_TYPE: TYPE_PART, KEY_TEXT: ''})


def add_noinclude_to_first_main_if_no_part(blocks: List[Dict[str, str]]) -> None:
    """
    Add <noinclude>༄༅། །</noinclude> to the first MAIN block on a page
    if there are no parts on that page.
    """
    noinclude_tag = "<noinclude>༄༅། །</noinclude>"
    
    for i in range(len(blocks)):
        if blocks[i].get(KEY_TYPE) == TYPE_PAGE:
            # Find next page boundary (exclusive)
            next_page_idx: Optional[int] = None
            for j in range(i + 1, len(blocks)):
                if blocks[j].get(KEY_TYPE) == TYPE_PAGE:
                    next_page_idx = j
                    break
            # Check segment before next page (or end)
            next_page_idx = next_page_idx if next_page_idx is not None else len(blocks)
            segment = blocks[i + 1:next_page_idx]
            
            # Check if there are any parts in the segment
            has_part = any(b.get(KEY_TYPE) == TYPE_PART for b in segment)
            
            # If no parts, find first MAIN block and add noinclude tag
            if not has_part:
                for block in segment:
                    if block.get(KEY_TYPE) == TYPE_MAIN:
                        text = block.get(KEY_TEXT, '')
                        # Add noinclude tag at the beginning if not already present
                        if noinclude_tag not in text:
                            block[KEY_TEXT] = f"{noinclude_tag}{text}"
                        break  # Only add to first MAIN block


def numerate_parts(blocks: List[Dict[str, str]]) -> None:
    """Number all part blocks sequentially as '## part1 ##', '## part2 ##', etc."""
    num = 1
    for block in blocks:
        if block.get(KEY_TYPE) == TYPE_PART:
            block[KEY_TEXT] = f"## part{num} ##"
            num += 1

def stringbuild_data(blocks: List[Dict[str, str]]) -> str:
    """
    Print the 'text' field for all blocks including 'heading'.
    After each block of type 'page' or 'part' always add a newline.
    After 'main' or 'heading', add a newline only if the next block exists and is 'page' or 'part'.
    Never add a newline after 'main' if the next block is also 'main'.
    """
    result_data = []
    n = len(blocks)
    for i, block in enumerate(blocks):
        btype = block.get(KEY_TYPE)
        text = block.get(KEY_TEXT, '')
        
        if text:
            result_data.append(text)

        if btype in (TYPE_PAGE, TYPE_PART):
            result_data.append('\n')
        elif btype in (TYPE_MAIN, TYPE_HEADING):
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
    add_noinclude_to_first_main_if_no_part(blocks)
    numerate_parts(blocks)
    result_text = stringbuild_data(blocks)
    return result_text