import os
import io
import json
import xml.etree.ElementTree as ET
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
from google import genai

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_key = os.environ.get("GOOGLE_API_KEY")
client = genai.Client(api_key=api_key) if api_key else None

@app.post("/analyze-sheet")
async def analyze_sheet(file: UploadFile = File(...)):
    if not client:
        raise HTTPException(status_code=500, detail="API Key missing on server.")
    try:
        content = await file.read()
        img = Image.open(io.BytesIO(content))
        if img.mode != 'RGB': img = img.convert('RGB')
        
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG")
        img_to_send = Image.open(buffer)

        # 🚀 프롬프트 정밀 강화: AI에게 음표를 찾는 '방법'을 교육합니다. [cite: 2026-03-11]
        prompt = """
        너는 숙련된 음악가이자 OMR(광학 악보 인식) 전문가야. 
        이 악보 이미지를 보고 다음 단계에 따라 분석해줘:
        
        1. 오선지의 각 마디를 순서대로 스캔해.
        2. 가사나 코드는 무시하고, 오직 멜로디 라인의 '음표(Note Head)'에만 집중해.
        3. 높은음자리표 기준, 오선지의 줄과 칸에 걸린 음표의 높이를 판별해 (예: C4, D4, E4).
        4. 음표의 기둥과 꼬리를 보고 박자를 판별해 (4분음표=4n, 8분음표=8n 등).
        
        출력은 반드시 다른 설명 없이 오직 아래 형식의 JSON 데이터만 해줘:
        { "melody": [ { "note": "G4", "duration": "4n", "time": "+0.0" }, ... ] }
        """

        response = client.models.generate_content(
            model='gemini-2.0-flash-001', 
            contents=[img_to_send, prompt]
        )
        
        # JSON 데이터만 깔끔하게 추출하는 로직 보강 [cite: 2026-03-11]
        raw_text = response.text
        start_idx = raw_text.find('{')
        end_idx = raw_text.rfind('}') + 1
        if start_idx == -1 or end_idx == 0:
            return {"melody": []}
            
        clean_json = raw_text[start_idx:end_idx]
        return json.loads(clean_json)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze-xml")
async def analyze_xml(file: UploadFile = File(...)):
    # MusicXML 분석 로직 유지
    try:
        content = await file.read()
        root = ET.fromstring(content)
        melody_data = []
        current_time = 0.0
        for measure in root.findall('.//measure'):
            for note in measure.findall('note'):
                if note.find('rest') is not None:
                    duration_node = note.find('duration')
                    if duration_node: current_time += float(duration_node.text) * 0.25 
                    continue
                pitch = note.find('pitch')
                if pitch:
                    step = pitch.find('step').text 
                    octave = pitch.find('octave').text 
                    note_name = f"{step}{octave}"
                    type_node = note.find('type')
                    duration_str = "4n" 
                    if type_node:
                        durations = {'whole':'1n', 'half':'2n', 'quarter':'4n', 'eighth':'8n', '16th':'16n'}
                        duration_str = durations.get(type_node.text, '4n')
                    melody_data.append({"note": note_name, "duration": duration_str, "time": f"+{current_time}"})
                    current_time += 0.5 if duration_str == '8n' else 1.0
        return {"melody": melody_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

