import os
import json
import io
import xml.etree.ElementTree as ET
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image

# 🚀 구글이 공식적으로 요구하는 최신 라이브러리를 사용합니다.
from google import genai
from google.genai import types

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
    return {"message": "노엘 뮤직 AI 서버 가동 중 (최신 SDK 적용 완료)!"}

# 목사님의 렌더 서버 환경변수 연동
api_key = os.getenv("APP_AI_KEY") or os.getenv("GOOGLE_API_KEY")
client = genai.Client(api_key=api_key) if api_key else None

# =========================================================
# [기능 1] 이미지 악보 분석 (최신 gemini-2.0-flash 모델 적용)
# =========================================================
@app.post("/analyze-sheet")
async def analyze_sheet(file: UploadFile = File(...)):
    if not client:
        return {"melody": []}
    try:
        content = await file.read()
        img = Image.open(io.BytesIO(content)).convert('RGB')
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG")
        
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=[
                types.Part.from_bytes(data=buffer.getvalue(), mime_type='image/jpeg'),
                "이 악보를 분석해서 JSON으로 변환해줘. 반드시 다음 형식으로만 대답해: {\"melody\": [{\"note\": \"C4\", \"duration\": \"4n\", \"time\": 0.0}]}. 다른 설명은 절대 하지 마."
            ],
            config=types.GenerateContentConfig(response_mime_type='application/json')
        )
        
        raw_text = response.text
        if not raw_text:
            return {"melody": []}
            
        clean_json = raw_text.replace('```json', '').replace('```', '').strip()
        return json.loads(clean_json)

    except Exception as e:
        print(f">>> [ERROR] 이미지 분석: {str(e)}")
        return {"melody": []}

# =========================================================
# [기능 2] MusicXML 정밀 분석 (사운드 엔진 호환성 극대화)
# =========================================================
@app.post("/analyze-xml")
async def analyze_xml(file: UploadFile = File(...)):
    try:
        content = await file.read()
        root = ET.fromstring(content)
        melody_data = []
        
        divisions = 1
        div_node = root.find('.//divisions')
        if div_node is not None: 
            divisions = int(div_node.text)
        
        seconds_per_beat = 0.5 
        current_time = 0.0
        
        for measure in root.findall('.//measure'):
            for note in measure.findall('note'):
                dur_node = note.find('duration')
                if dur_node is None: 
                    continue
                
                dur_val = int(dur_node.text)
                note_dur_sec = (dur_val / divisions) * seconds_per_beat
                
                if note.find('rest') is not None:
                    current_time += note_dur_sec
                    continue
                
                pitch = note.find('pitch')
                if pitch:
                    step = pitch.find('step').text
                    octave = pitch.find('octave').text
                    note_name = step
                    
                    # 변화표(샵, 플랫) 정밀 처리
                    alter = pitch.find('alter')
                    if alter is not None:
                        if alter.text == '1': note_name += '#'
                        elif alter.text == '-1': note_name += 'b'
                    note_name += octave
                    
                    melody_data.append({
                        "note": note_name, 
                        "duration": "4n", 
                        "time": float(current_time) 
                    })
                    current_time += note_dur_sec
                    
        return {"melody": melody_data}
    except Exception as e:
        print(f">>> [ERROR] XML 분석: {str(e)}")
        return {"melody": []}

