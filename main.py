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

@app.get("/")
async def root():
    return {"message": "노엘 뮤직 AI 서버가 정상 가동 중입니다!"}

# [기능 1] 이미지 악보 분석 (호환성 최강 모델로 변경)
@app.post("/analyze-sheet")
async def analyze_sheet(file: UploadFile = File(...)):
    if not client: raise HTTPException(status_code=500, detail="API Key missing")
    try:
        content = await file.read()
        img = Image.open(io.BytesIO(content)).convert('RGB')
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG")
        
        # 🚀 가장 안정적인 gemini-1.5-flash로 변경하여 404 에러를 원천 차단합니다.
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=[
                types.Part.from_bytes(data=buffer.getvalue(), mime_type='image/jpeg'),
                "이 악보의 멜로디를 분석해서 JSON 데이터로 변환해줘. melody 키 안에 note, duration, time을 넣어줘."
            ],
            config=types.GenerateContentConfig(response_mime_type='application/json')
        )
        return response.parsed
    except Exception as e:
        print(f">>> [ERROR] 이미지 분석 실패: {str(e)}")
        # 분석 실패 시에도 빈 배열을 주어 화면이 멈추지 않게 합니다.
        return {"melody": []}

# [기능 2] MusicXML 정밀 분석
@app.post("/analyze-xml")
async def analyze_xml(file: UploadFile = File(...)):
    try:
        content = await file.read()
        root = ET.fromstring(content)
        melody_data = []
        divisions = 1
        div_node = root.find('.//divisions')
        if div_node is not None: divisions = int(div_node.text)
        current_time = 0.0
        for measure in root.findall('.//measure'):
            for note in measure.findall('note'):
                dur_node = note.find('duration')
                dur_val = int(dur_node.text) if dur_node is not None else divisions
                if note.find('rest') is not None:
                    current_time += (dur_val / divisions)
                    continue
                pitch = note.find('pitch')
                if pitch:
                    note_name = f"{pitch.find('step').text}{pitch.find('octave').text}"
                    melody_data.append({"note": note_name, "duration": "4n", "time": f"+{current_time}"})
                    current_time += (dur_val / divisions)
        return {"melody": melody_data}
    except Exception as e:
        print(f">>> [ERROR] XML 분석 실패: {str(e)}")
        return {"melody": []}



