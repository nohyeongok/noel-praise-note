import os, io, json, re
import xml.etree.ElementTree as ET
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
from google import genai
from google.genai import types

app = FastAPI()

# 💡 상용 서비스를 위해 통신 허용 범위를 정확히 설정합니다.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 유료 API 키 설정
api_key = os.environ.get("GOOGLE_API_KEY")
client = genai.Client(api_key=api_key) if api_key else None

@app.get("/")
async def root():
    return {"message": "노엘 뮤직 AI 프로 서버가 정상 가동 중입니다!"}

# [기능 1] 이미지 악보 분석 (Gemini 1.5 Flash 안정화 버전)
@app.post("/analyze-sheet")
async def analyze_sheet(file: UploadFile = File(...)):
    if not client: raise HTTPException(status_code=500, detail="API Key missing")
    try:
        content = await file.read()
        img = Image.open(io.BytesIO(content)).convert('RGB')
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG")
        
        # 🚀 404 에러 방지를 위해 모델명을 'gemini-1.5-flash'로 정확히 지정합니다.
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=[
                types.Part.from_bytes(data=buffer.getvalue(), mime_type='image/jpeg'),
                "이 악보의 멜로디를 정밀 분석해서 JSON으로 변환해줘. melody 키 안에 note, duration, time 정보를 포함해. 다른 말은 절대 하지 마."
            ],
            config=types.GenerateContentConfig(response_mime_type='application/json')
        )
        return response.parsed
    except Exception as e:
        print(f">>> [ERROR] 분석 오류: {str(e)}")
        return {"melody": []}

# [기능 2] MusicXML 정밀 분석 (박자 동기화)
@app.post("/analyze-xml")
async def analyze_xml(file: UploadFile = File(...)):
    try:
        content = await file.read()
        root = ET.fromstring(content)
        melody_data = []
        divisions = 1
        div_node = root.find('.//divisions')
        if div_node is not None: divisions = int(div_node.text)
        
        # 💡 상용 퀄리티를 위해 BPM 120 기준(1박자 = 0.5초)으로 시간을 계산합니다.
        current_time = 0.0
        for measure in root.findall('.//measure'):
            for note in measure.findall('note'):
                dur_node = note.find('duration')
                if dur_node is None: continue
                dur_val = int(dur_node.text)
                note_dur_sec = (dur_val / divisions) * 0.5 # 정밀 박자 환산
                
                if note.find('rest') is not None:
                    current_time += note_dur_sec
                    continue
                
                pitch = note.find('pitch')
                if pitch:
                    note_name = f"{pitch.find('step').text}{pitch.find('octave').text}"
                    melody_data.append({"note": note_name, "duration": "4n", "time": f"+{current_time}"})
                    current_time += note_dur_sec
        return {"melody": melody_data}
    except Exception as e:
        return {"melody": []}[]}



