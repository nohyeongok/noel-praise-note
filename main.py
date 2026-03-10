import os, io, json, re
import xml.etree.ElementTree as ET
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
from google import genai
from google.genai import types

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

api_key = os.environ.get("GOOGLE_API_KEY")
client = genai.Client(api_key=api_key) if api_key else None

@app.post("/analyze-sheet")
async def analyze_sheet(file: UploadFile = File(...)):
    if not client: raise HTTPException(status_code=500, detail="API Key missing")
    try:
        content = await file.read()
        img = Image.open(io.BytesIO(content)).convert('RGB')
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG")
        
        # 🚀 AI에게 더 구체적으로 '음표 인식' 사역을 명령합니다. [cite: 2026-03-11]
        prompt = """
        너는 전 세계 모든 찬양 악보를 읽을 수 있는 AI 음악 전문가야. 
        이 악보 이미지를 보고 다음 규칙에 따라 멜로디를 추출해줘:
        1. 가사와 코드는 무시하고, 오직 오선지 위의 '음표' 위치만 찾아.
        2. 높은음자리표를 기준으로 각 음표의 음정(C4, D4 등)을 판별해.
        3. 음표의 모양에 따라 박자(4분음표=4n, 8분음표=8n)를 결정해.
        4. 반드시 'melody'라는 키를 가진 JSON 형식으로만 대답해.
        """

        response = client.models.generate_content(
            model='gemini-2.0-flash-001',
            contents=[
                types.Part.from_bytes(data=buffer.getvalue(), mime_type='image/jpeg'),
                prompt
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
        # AI의 대답을 로그에 남겨 추후 분석을 돕습니다. [cite: 2026-03-11]
        print(f">>> [LOG] AI 분석 결과: {response.text}")
        return response.parsed
    except Exception as e:
        print(f">>> [ERROR] 분석 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze-xml")
async def analyze_xml(file: UploadFile = File(...)):
    # MusicXML 분석 로직 유지 [cite: 2026-03-11]
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
        raise HTTPException(status_code=500, detail=str(e))




