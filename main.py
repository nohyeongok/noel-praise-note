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
    return {"message": "노엘 뮤직 AI 서버 가동 중!"}

# [기능 1] 이미지 악보 분석 (모델명 최적화)
@app.post("/analyze-sheet")
async def analyze_sheet(file: UploadFile = File(...)):
    if not client: raise HTTPException(status_code=500, detail="API Key missing")
    try:
        content = await file.read()
        img = Image.open(io.BytesIO(content)).convert('RGB')
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG")
        
        # 🚀 모델명을 'gemini-1.5-flash-latest'로 지정하여 인식률을 높입니다.
        response = client.models.generate_content(
            model='gemini-1.5-flash-latest',
            contents=[
                types.Part.from_bytes(data=buffer.getvalue(), mime_type='image/jpeg'),
                "이 악보의 멜로디를 분석해서 JSON 데이터로 변환해줘. melody 키 안에 note, duration, time을 넣어줘."
            ],
            config=types.GenerateContentConfig(response_mime_type='application/json')
        )
        return response.parsed
    except Exception as e:
        print(f">>> [ERROR] 분석 실패: {str(e)}")
        return {"melody": []}

# [기능 2] MusicXML 정밀 분석 (박자 100% 동기화)
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
                if dur_node is None: continue
                dur_val = int(dur_node.text)
                
                # 💡 음표의 실제 길이 계산 (박자가 어긋나지 않게 함)
                beat_val = dur_val / divisions
                tone_dur = "4n"
                if beat_val >= 4: tone_dur = "1n"
                elif beat_val >= 2: tone_dur = "2n"
                elif beat_val >= 1: tone_dur = "4n"
                elif beat_val >= 0.5: tone_dur = "8n"
                else: tone_dur = "16n"

                if note.find('rest') is not None:
                    current_time += beat_val
                    continue
                
                pitch = note.find('pitch')
                if pitch:
                    note_name = f"{pitch.find('step').text}{pitch.find('octave').text}"
                    melody_data.append({"note": note_name, "duration": tone_dur, "time": f"+{current_time}"})
                    current_time += beat_val
        return {"melody": melody_data}
    except Exception as e:
        return {"melody": []}






