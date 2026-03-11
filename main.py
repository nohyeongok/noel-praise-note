import os
import json
import io
import xml.etree.ElementTree as ET
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
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
    return {"message": "노엘 뮤직 AI 서버 가동 중 (BPM 자동 인식 탑재)!"}

api_key = os.getenv("APP_AI_KEY") or os.getenv("GOOGLE_API_KEY")
client = genai.Client(api_key=api_key) if api_key else None

# [기능 1] 이미지 악보 분석 (기존 정밀 해독 로직 유지)
@app.post("/analyze-sheet")
async def analyze_sheet(file: UploadFile = File(...)):
    if not client: return {"melody": []}
    try:
        content = await file.read()
        img = Image.open(io.BytesIO(content)).convert('RGB')
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG")
        
        prompt = """너는 프로 악보 해독가야. 오선지를 정확히 스캔해서 JSON으로 변환해줘.
        형식: {"melody": [{"note": "C4", "duration": "4n", "time": 0.0}]}"""

        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[types.Part.from_bytes(data=buffer.getvalue(), mime_type='image/jpeg'), prompt],
            config=types.GenerateContentConfig(response_mime_type='application/json')
        )
        clean_json = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(clean_json)
    except Exception as e:
        return {"melody": []}

# [기능 2] MusicXML 정밀 분석 (사용자 지정 BPM 반영 로직)
@app.post("/analyze-xml")
async def analyze_xml(file: UploadFile = File(...), bpm: float = None): # 💡 bpm 파라미터 추가
    try:
        content = await file.read()
        root = ET.fromstring(content)
        melody_data = []
        
        # 💡 로직 우선순위: 1.사용자 선택값 -> 2.악보 내부값 -> 3.기본값(142)
        final_bpm = 142.0       
        if bpm is not None:
    # 💡 프론트엔드 설정에 맞춰 최소값을 60으로 제한합니다.
    final_bpm = max(60.0, bpm)
    
            print(f">>> [LOG] 사용자 지정 BPM 적용: {final_bpm}")
        else:
            tempo_node = root.find('.//per-minute')
            if tempo_node is not None:
                try:
                    final_bpm = float(tempo_node.text)
                    print(f">>> [LOG] 악보 고유 BPM 감지: {final_bpm}")
                except: pass
        
        seconds_per_beat = 60.0 / final_bpm
        
        divisions = 1
        div_node = root.find('.//divisions')
        if div_node is not None: divisions = int(div_node.text)
        
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
                    # (이전의 음정 및 시간 계산 로직 동일)
                    step = pitch.find('step').text
                    octave = pitch.find('octave').text
                    note_name = step
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
                    
        return {"melody": melody_data, "applied_bpm": final_bpm}
    except Exception as e:
        return {"melody": []}

