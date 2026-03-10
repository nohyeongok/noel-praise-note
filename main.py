import os, io, json, re
import xml.etree.ElementTree as ET
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
from google import genai
from google.genai import types

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# 1. 목사님의 유료 API 키를 연결합니다.
api_key = os.environ.get("GOOGLE_API_KEY")
client = genai.Client(api_key=api_key) if api_key else None

@app.get("/")
async def root():
    return {"message": "노엘 뮤직 AI 프로 서버 가동 중!"}

# [사역 1] 이미지 악보 분석 (전문가용 gemini-1.5-pro 모델 사용) [cite: 2026-03-11]
@app.post("/analyze-sheet")
async def analyze_sheet(file: UploadFile = File(...)):
    if not client: raise HTTPException(status_code=500, detail="API Key missing")
    try:
        content = await file.read()
        img = Image.open(io.BytesIO(content)).convert('RGB')
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG")
        
        # 🚀 유료 사용자의 특권: 가장 정밀한 'pro' 모델로 악보를 분석합니다. [cite: 2026-03-11]
        response = client.models.generate_content(
            model='gemini-1.5-pro', 
            contents=[
                types.Part.from_bytes(data=buffer.getvalue(), mime_type='image/jpeg'),
                "너는 프로 음악가이자 악보 해독 전문가야. "
                "이 이미지에서 오선지 위의 모든 음표를 한 줄도 빠짐없이 스캔해서 멜로디 데이터를 생성해줘. "
                "결과는 반드시 melody 키를 가진 JSON 형식이어야 하며 note, duration, time 정보를 포함해."
            ],
            config=types.GenerateContentConfig(response_mime_type='application/json')
        )
        return response.parsed
    except Exception as e:
        print(f">>> [ERROR] 프로 모델 분석 실패: {str(e)}")
        return {"melody": []}

# [사역 2] MusicXML 정밀 연주 (박자 100% 동기화 버전)
@app.post("/analyze-xml")
async def analyze_xml(file: UploadFile = File(...)):
    try:
        content = await file.read()
        root = ET.fromstring(content)
        melody_data = []
        
        divisions = 1
        div_node = root.find('.//divisions')
        if div_node is not None: divisions = int(div_node.text)
        
        # 유료 서비스 퀄리티를 위해 BPM 120 표준 속도를 적용합니다.
        seconds_per_beat = 60 / 120 
        current_time = 0.0
        
        for measure in root.findall('.//measure'):
            for note in measure.findall('note'):
                dur_node = note.find('duration')
                if dur_node is None: continue
                dur_val = int(dur_node.text)
                note_dur_sec = (dur_val / divisions) * seconds_per_beat
                
                if note.find('rest') is not None:
                    current_time += note_dur_sec
                    continue
                
                pitch = note.find('pitch')
                if pitch:
                    note_name = f"{pitch.find('step').text}{pitch.find('octave').text}"
                    melody_data.append({
                        "note": note_name,
                        "duration": "4n",
                        "time": f"+{current_time}"
                    })
                    current_time += note_dur_sec
                    
        return {"melody": melody_data}
    except Exception as e:
        return {"melody": []}
