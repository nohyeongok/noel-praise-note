import os
import io
import json
import xml.etree.ElementTree as ET
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
from google import genai

# 1. 서버 심장부 설정
app = FastAPI()

# 2. 웹 브라우저 통신 허용 (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. 제미나이 AI 연결 (Render의 Environment 설정에 넣으신 API Key를 자동으로 읽어옵니다)
api_key = os.environ.get("GOOGLE_API_KEY")
if not api_key:
    client = None
    print(">>> [경고] API Key가 설정되지 않았습니다.")
else:
    client = genai.Client(api_key=api_key)

# =========================================================
# [기능 1] 이미지 악보 분석 (main1.php에서 사용)
# =========================================================
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

        response = client.models.generate_content(
            model='gemini-2.0-flash-001', 
            contents=[
                img_to_send, 
                "이 악보 이미지를 정밀 분석하여 실제 음표와 박자 데이터를 JSON으로 추출해줘. "
                "반드시 { 'melody': [ { 'note': 'C4', 'duration': '4n', 'time': '+0.0' }, ... ] } 형식을 지키고, "
                "이미지에 보이는 실제 음정(C4, D4 등)과 박자(4분음표=4n, 8분음표=8n)를 최대한 반영해. "
                "다른 설명 없이 JSON 데이터만 출력해."
            ]
        )
        clean_json = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(clean_json)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# =========================================================
# [기능 2] MusicXML 분석 (main5.html에서 사용)
# =========================================================
@app.post("/analyze-xml")
async def analyze_xml(file: UploadFile = File(...)):
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
                    
                    alter = pitch.find('alter')
                    if alter:
                        if alter.text == '1': note_name = f"{step}#{octave}"
                        elif alter.text == '-1': note_name = f"{step}b{octave}"
                    
                    type_node = note.find('type')
                    duration_str = "4n" 
                    if type_node:
                        type_val = type_node.text
                        durations = {'whole':'1n', 'half':'2n', 'quarter':'4n', 'eighth':'8n', '16th':'16n'}
                        duration_str = durations.get(type_val, '4n')
                    
                    melody_data.append({"note": note_name, "duration": duration_str, "time": f"+{current_time}"})
                    current_time += 0.5 if duration_str == '8n' else 1.0
        
        return {"melody": melody_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"XML 분석 오류: {str(e)}")
