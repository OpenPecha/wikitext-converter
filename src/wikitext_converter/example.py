import os
from typing import Optional
from wikitext_converter.doc_to_wiki import convert


def main(doc_file_path: str, output_file_path: Optional[str] = None):
    """
    Convert DOCX file to Wikitext and optionally save to file.
    
    Args:
        doc_file_path: Path to the input DOCX file.
        output_file_path: Optional path to the output file. If provided, the result
                         will be saved to this file. Can include directory path.
    """
    try:
        # Convert DOCX to Wikitext string
        wikitext_result = convert(doc_file_path)
        
        # Save result to file if output path is provided
        if output_file_path:
            # Create directory if it doesn't exist
            output_dir = os.path.dirname(output_file_path)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
            
            with open(output_file_path, 'w', encoding='utf-8') as f:
                f.write(wikitext_result)
            
            print(f"Conversion completed successfully!")
            print(f"Input: {doc_file_path}")
            print(f"Output: {output_file_path}")
        else:
            print(f"Conversion completed successfully!")
            print(f"Input: {doc_file_path}")
            print("Result (not saved to file):")
            print(wikitext_result)
        
    except FileNotFoundError:
        print(f"Error: File '{doc_file_path}' not found.")
    except Exception as e:
        print(f"Error during conversion: {e}")


if __name__ == "__main__":
    # Example usage
    main("input.docx", "output.txt")
