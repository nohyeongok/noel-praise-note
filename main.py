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

# [기능 1] 이미지 악보 분석 (main1.php 용) - 모델명 최적화
@app.post("/analyze-sheet")
async def analyze_sheet(file: UploadFile = File(...)):
    try:
        # ... 이미지 처리 로직 ...
        prompt = """
        너는 프로 음악가이자 악보 해독 전문가야. 
        1. 이미지에서 오선지의 조표(Sharp/Flat)와 박자표를 먼저 확인해.
        2. 모든 음표를 마디 단위로 정밀 스캔하여 절대적인 음높이와 길이를 계산해.
        3. 결과는 반드시 연주가 가능한 완벽한 JSON 형식이어야 하며, 
           단 하나의 음표도 누락하지 마.
        """
        response = client.models.generate_content(
            model='gemini-1.5-pro', # 퀄리티를 위해 Pro 모델 사용
            contents=[img_to_send, prompt],
            config=types.GenerateContentConfig(response_mime_type='application/json')
        )
        return response.parsed
    except Exception as e:
        return {"melody": [], "error": str(e)}

# [기능 2] MusicXML 정밀 분석 (main5.html 용 - 박자 속도 100% 동기화)
@app.post("/analyze-xml")
async def analyze_xml(file: UploadFile = File(...)):
    try:
        content = await file.read()
        root = ET.fromstring(content)
        melody_data = []
        
        # XML 박자의 기준점(divisions)을 찾습니다.
        divisions = 1
        div_node = root.find('.//divisions')
        if div_node is not None: divisions = int(div_node.text)
        
        # 💡 BPM 120 기준으로 박자 속도를 정밀하게 계산합니다. (1박자 = 0.5초)
        bpm = 120
        seconds_per_beat = 60 / bpm 
        current_time = 0.0
        
        for measure in root.findall('.//measure'):
            for note in measure.findall('note'):
                dur_node = note.find('duration')
                if dur_node is None: continue
                dur_val = int(dur_node.text)
                
                # 실제 연주 시간 계산: (음표길이 / 기준박자) * 초당박수
                note_duration_seconds = (dur_val / divisions) * seconds_per_beat
                
                if note.find('rest') is not None:
                    current_time += note_duration_seconds
                    continue
                
                pitch = note.find('pitch')
                if pitch:
                    note_name = f"{pitch.find('step').text}{pitch.find('octave').text}"
                    melody_data.append({
                        "note": note_name,
                        "duration": "4n",
                        "time": f"+{current_time}"
                    })
                    current_time += note_duration_seconds
                    
        return {"melody": melody_data}
    except Exception as e:
        print(f">>> [ERROR] XML 분석 실패: {str(e)}")
        return {"melody": []}[]}








