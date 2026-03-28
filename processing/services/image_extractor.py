import io
from PIL import Image
from processing.core.config import settings
from tenacity import retry, stop_after_attempt, wait_exponential
from google import genai
import easyocr
import cv2
import numpy as np

# Initialize Gemini client if key exists
_client = (
    genai.Client(api_key=settings.GEMINI_API_KEY) if settings.GEMINI_API_KEY else None
)

# Initialize EasyOCR Reader globally (memoized)
ocr_reader = None


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=4, max=20))
async def extract_text_from_image(image_bytes: bytes) -> str:
    """
    Extracts text natively from images.
    Attempts to use Gemini 2.0 Vision if an API key is provided for highest quality OCR.
    Falls back gracefully to the local EasyOCR model if Gemini is totally unavailable.
    """
    if _client:
        try:
            image = Image.open(io.BytesIO(image_bytes))
            prompt = (
                "Extract all readable text from this image exactly as written. "
                "If there are tables or forms, try to maintain their logical structure. "
                "Do NOT invent text. If there is no text, return an empty string."
            )
            response = await _client.aio.models.generate_content(
                model="gemini-2.0-flash",
                contents=[prompt, image],
            )
            return response.text
        except Exception as e:
            print(f"[ERROR!] Gemini Vision failed, falling back to EasyOCR: {e}")

    # Fallback to local EasyOCR
    global ocr_reader
    if ocr_reader is None:
        print("[*] Initializing local EasyOCR model into memory...")
        ocr_reader = easyocr.Reader(["en"])  # Load English by default for OCR fallback

    # Convert pure bytes to a math-ready numpy array structure
    nparr = np.frombuffer(image_bytes, np.uint8)
    cv_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    # 1. Convert to purely grayscale to drop channel noise
    gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)

    # 2. Apply a strict Gaussian blur to explicitly remove scan artifacts
    blur = cv2.GaussianBlur(gray, (5, 5), 0)

    # 3. Apply Otsu's mathematical thresholding to violently binarize the image (black/white)
    _, thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # Pass the perfectly polished binary frame into the OCR reader
    results = ocr_reader.readtext(thresh, detail=0)
    return " ".join(results)
