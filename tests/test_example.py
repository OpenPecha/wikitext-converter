from pathlib import Path

from wikitext_converter.doc_to_wiki import convert


def test_convert_heart_sutra():
    """Test conversion of heart sutra DOCX file to Wikitext."""
    # Get the test data directory
    test_dir = Path(__file__).parent
    data_dir = test_dir / "data"
    
    # Input and expected output files
    input_file = data_dir / "heart sutra.docx"
    expected_file = data_dir / "heart_sutra_wiki.txt"
    
    # Verify files exist
    assert input_file.exists(), f"Input file not found: {input_file}"
    assert expected_file.exists(), f"Expected file not found: {expected_file}"
    
    # Read expected result
    with open(expected_file, 'r', encoding='utf-8') as f:
        expected_text = f.read()
    
    # Convert DOCX to Wikitext
    result_text = convert(str(input_file))
    
    # Save result to file for debugging
    result_file = data_dir / "result_text.txt"
    with open(result_file, 'w', encoding='utf-8') as f:
        f.write(result_text)
    
    # Compare results (pytest will show diff automatically)
    assert result_text == expected_text, "Converted text does not match expected output"
