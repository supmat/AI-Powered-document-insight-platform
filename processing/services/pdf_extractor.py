import fitz


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """
    Extracts text sequentially from all pages in a PDF document.
    """
    text = ""
    # Open the PDF directly from the byte stream
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    for page in doc:
        extracted = page.get_text()
        if extracted:
            text += extracted + "\n\n"

    doc.close()
    return text.strip()
