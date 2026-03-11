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
    return {"message": "노엘 뮤직 AI 서버 가동 중 (정밀 해독 & 속도 조율 완료)!"}

api_key = os.getenv("APP_AI_KEY") or os.getenv("GOOGLE_API_KEY")
client = genai.Client(api_key=api_key) if api_key else None

# =========================================================
# [기능 1] 이미지 악보 분석 (AI에게 강력한 정밀 해독 명령 부여)
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
        
        # 💡 AI가 대충 지어내지 못하도록 프롬프트(명령어)를 아주 엄격하게 바꿨습니다.
        prompt = """너는 프로 악보 해독가야. 첨부된 악보 이미지의 오선지를 한 음도 빠짐없이 정확히 스캔해.
        조표(Sharp/Flat)와 박자표를 반드시 반영해서, 실제 악보에 그려진 멜로디의 정확한 음정(note), 길이(duration), 시작 시간(time)을 계산해. 
        반드시 다음 JSON 형식으로만 대답해: {"melody": [{"note": "C4", "duration": "4n", "time": 0.0}]}
        절대로 임의의 멜로디를 지어내지 말고, 악보에 있는 그대로만 추출해. 다른 설명은 쓰지 마."""

        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[
                types.Part.from_bytes(data=buffer.getvalue(), mime_type='image/jpeg'),
                prompt
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
# [기능 2] MusicXML 정밀 분석 (찬양 템포에 맞춰 속도 향상)
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
        
        # 💡 기존 0.5초(BPM 120)에서 0.42초(BPM 약 142)로 줄여서 찬양을 더 경쾌하고 빠르게 연주합니다!
        seconds_per_beat = 0.42 
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
