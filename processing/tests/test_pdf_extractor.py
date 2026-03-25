from processing.services.pdf_extractor import extract_text_from_pdf
import fitz


def test_pdf_extraction():
    # Create an empty PDF strictly for memory testing
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Hello World PDF Testing")
    pdf_bytes = doc.write()
    doc.close()

    text = extract_text_from_pdf(pdf_bytes)
    assert "Hello World PDF Testing" in text
