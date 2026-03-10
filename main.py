import os
import json
import io
import xml.etree.ElementTree as ET
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai
from PIL import Image

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "노엘 뮤직 AI 서버가 완벽하게 가동 중입니다!"}

api_key = os.getenv("APP_AI_KEY") or os.getenv("GOOGLE_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

# =========================================================
# [기능 1] 이미지 악보 분석 (404 에러 방지용 flash 모델)
# =========================================================
@app.post("/analyze-sheet")
async def analyze_sheet(file: UploadFile = File(...)):
    try:
        content = await file.read()
        img = Image.open(io.BytesIO(content))
        if img.mode != 'RGB': 
            img = img.convert('RGB')
        
        # 🚀 404 에러가 나지 않는 가장 안정적인 모델명으로 고정합니다.
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = """이 악보를 분석해서 JSON으로 변환해줘. 
        반드시 다음 형식으로만 대답해: 
        {"melody": [{"note": "C4", "duration": "4n", "time": 0.0}]}
        주의: time 값에는 절대 + 기호를 넣지 말고 순수한 숫자(예: 0.0, 0.5)로 출력해."""
        
        response = model.generate_content([img, prompt])
        
        clean_json = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(clean_json)

    except Exception as e:
        print(f">>> [ERROR] 이미지 분석: {str(e)}")
        return {"melody": []}

# =========================================================
# [기능 2] MusicXML 정밀 분석 (사운드 엔진 충돌 해결)
# =========================================================
@app.post("/analyze-xml")
async def analyze_xml(file: UploadFile = File(...)):
    try:
        content = await file.read()
        root = ET.fromstring(content)
        melody_data = []
        
        divisions = 1
        div_node = root.find('.//divisions')
        if div_node is not None: divisions = int(div_node.text)
        
        seconds_per_beat = 0.5 
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
                        # 💡 핵심 해결: + 기호를 빼고 순수 숫자로만 소리 엔진에 전달합니다!
                        "time": float(current_time) 
                    })
                    current_time += note_dur_sec
                    
        return {"melody": melody_data}
    except Exception as e:
        print(f">>> [ERROR] XML 분석: {str(e)}")
        return {"melody": []}

