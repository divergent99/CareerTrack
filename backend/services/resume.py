from pypdf import PdfReader
import io

def extract_resume_text(file_bytes):
    reader = PdfReader(io.BytesIO(file_bytes))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    return text.strip()