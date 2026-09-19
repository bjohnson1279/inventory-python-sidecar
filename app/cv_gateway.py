import base64
import random
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/cv", tags=["Computer Vision Gateway"])

class AnalyzeInboundRequest(BaseModel):
    image_base64: str = Field(..., max_length=5000000, description="Base64 encoded image string")
    po_id: str = Field(None, max_length=255, description="Optional Purchase Order ID for context")

class Dimensions(BaseModel):
    length: float = Field(..., ge=0.0)
    width: float = Field(..., ge=0.0)
    height: float = Field(..., ge=0.0)

class AnalyzeInboundResponse(BaseModel):
    dimensions: Dimensions
    ocr_text: str = Field(..., max_length=5000)
    anomaly_score: float = Field(..., ge=0.0, le=1.0)
    has_damage: bool

@router.post("/analyze-inbound", response_model=AnalyzeInboundResponse)
def analyze_inbound(req: AnalyzeInboundRequest):
    try:
        # Decode the image to ensure it's valid base64
        # Since we are mocking OpenCV / PyTesseract for the POC:
        # image_data = base64.b64decode(req.image_base64)
        pass
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 image data")

    # Mock Dimensioning based on contour approximations
    # In a real scenario, this would use cv2.findContours and perspective transformation
    length = round(random.uniform(10.0, 50.0), 2)
    width = round(random.uniform(10.0, 50.0), 2)
    height = round(random.uniform(5.0, 30.0), 2)
    
    # Mock OCR Recovery
    # Real scenario would use pytesseract.image_to_string(image)
    # We will just generate a fake supplier string if there's an image.
    supplier_str = f"SUPPLIER-{random.randint(1000, 9999)}"

    # Mock Anomaly / Damage Detection
    # Real scenario: Edge detection (Canny) variance or a lightweight YOLO model
    anomaly_score = round(random.uniform(0.0, 1.0), 2)
    has_damage = anomaly_score > 0.75

    return AnalyzeInboundResponse(
        dimensions=Dimensions(length=length, width=width, height=height),
        ocr_text=supplier_str,
        anomaly_score=anomaly_score,
        has_damage=has_damage
    )
