import os, io, json, re
import xml.etree.ElementTree as ET
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
from google import genai
from google.genai import types

app = FastAPI()

# 웹 브라우저 통신 허용 설정
app.add_middleware(
    CORSMiddleware, 
    allow_origins=["*"], 
    allow_credentials=True, 
    allow_methods=["*"], 
    allow_headers=["*"]
)

# Render 환경 변수에 설정한 API 키를 읽어옵니다.
api_key = os.environ.get("GOOGLE_API_KEY")
client = genai.Client(api_key=api_key) if api_key else None

# =========================================================
# [기능 1] 이미지 악보 분석 (모델 이름 수정됨)
# =========================================================
@app.post("/analyze-sheet")
async def analyze_sheet(file: UploadFile = File(...)):
    if not client: 
        raise HTTPException(status_code=500, detail="API Key missing on server.")
    try:
        content = await file.read()
        img = Image.open(io.BytesIO(content)).convert('RGB')
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG")
        
        # 🚀 모델 명칭을 'gemini-2.0-flash'로 수정하여 404 에러를 해결합니다. [cite: 2026-03-11]
        response = client.models.generate_content(
            model='gemini-2.0-flash', 
            contents=[
                types.Part.from_bytes(data=buffer.getvalue(), mime_type='image/jpeg'),
                "이 악보의 멜로디를 분석해서 연주 가능한 JSON 데이터로 변환해줘. "
                "반드시 melody라는 키 안에 note, duration, time 정보를 포함해야 해."
            ],
            config=types.GenerateContentConfig(
                response_mime_type='application/json',
                response_schema={
                    "type": "OBJECT",
                    "properties": {
                        "melody": {
                            "type": "ARRAY",
                            "items": {
                                "type": "OBJECT",
                                "properties": {
                                    "note": {"type": "STRING"},
                                    "duration": {"type": "STRING"},
                                    "time": {"type": "STRING"}
                                },
                                "required": ["note", "duration", "time"]
                            }
                        }
                    },
                    "required": ["melody"]
                }
            )
        )
        # AI가 분석한 데이터 반환
        return response.parsed
    except Exception as e:
        print(f">>> [ERROR] 분석 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# =========================================================
# [기능 2] MusicXML 분석 (기존 로직 유지)
# =========================================================
@app.post("/analyze-xml")
async def analyze_xml(file: UploadFile = File(...)):
    try:
        content = await file.read()
        root = ET.fromstring(content)
        melody_data = []
        current_time = 0.0
        for measure in root.findall('.//measure'):
            for note in measure.findall('note'):
                if note.find('rest') is not None:
                    dur = note.find('duration')
                    if dur: current_time += float(dur.text) * 0.25 
                    continue
                pitch = note.find('pitch')
                if pitch:
                    note_name = f"{pitch.find('step').text}{pitch.find('octave').text}"
                    melody_data.append({"note": note_name, "duration": "4n", "time": f"+{current_time}"})
                    current_time += 1.0
        return {"melody": melody_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"XML 분석 오류: {str(e)}")
