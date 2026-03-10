import os, io, json, re
import xml.etree.ElementTree as ET
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
from google import genai

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
        
        # 🚀 AI에게 음표 위치를 더 정밀하게 찾으라고 명령 (프롬프트 강화) [cite: 2026-03-11]
        prompt = "이 악보를 분석해서 오직 { 'melody': [ { 'note': 'G4', 'duration': '4n', 'time': '+0.0' } ] } 형식의 JSON 데이터만 출력해. 설명은 일절 배제해."
        response = client.models.generate_content(model='gemini-2.0-flash-001', contents=[Image.open(buffer), prompt])
        
        # 💡 지저분한 텍스트에서 JSON 데이터만 쏙 뽑아내는 정밀 추출기 [cite: 2026-03-11]
        match = re.search(r'\{.*\}', response.text, re.DOTALL)
        if not match: return {"melody": []}
        return json.loads(match.group())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze-xml")
async def analyze_xml(file: UploadFile = File(...)):
    # MusicXML 분석 로직 (현재 정상 작동 중인 로직 유지) [cite: 2026-03-11]
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


