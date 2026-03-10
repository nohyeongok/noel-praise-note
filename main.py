import os
import io
import json
import xml.etree.ElementTree as ET
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
from google import genai

# 1. FastAPI 서버 심장부 (이 부분이 지워져서 에러가 났었습니다)
app = FastAPI()

# 2. CORS 설정 (웹 화면과 서버가 자유롭게 통신하도록 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# API 키가 설정되어 있는지 확인하고 클라이언트를 실행합니다.
api_key = os.environ.get("GOOGLE_API_KEY")
if not api_key:
    print(">>> [WARNING] GOOGLE_API_KEY가 설정되지 않았습니다. Render 환경 변수를 확인하세요.")
    client = None
else:
    client = genai.Client(api_key=api_key)
# 3. 제미나이 AI 클라이언트 준비
client = genai.Client()

# =========================================================
# [사역 1] 악보 스캔 & 연주 (이미지 전용) - main1.php 담당
# =========================================================
@app.post("/analyze-sheet")
async def analyze_sheet(file: UploadFile = File(...)):
    print(f">>> [LOG] 이미지 악보 분석 요청 수신: {file.filename}")
    try:
        content = await file.read()
        img = Image.open(io.BytesIO(content))
        
        # BMP 형식을 안전하게 변환
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG")
        img_to_send = Image.open(buffer)

        response = client.models.generate_content(
            model='gemini-2.0-flash-001', 
            contents=[
                img_to_send, 
                "이 악보를 분석해서 {melody: [{note: 'C4', duration: '4n', time: '0:0:0'}]} 형식의 JSON 데이터만 출력해줘."
            ]
        )
        
        clean_json = response.text.replace('```json', '').replace('```', '').strip()
        print(">>> [LOG] 이미지 악보 분석 성공!")
        return json.loads(clean_json)

    except Exception as e:
        print(f">>> [ERROR] 이미지 분석 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# =========================================================
# [사역 2] MusicXML 임포트 (XML 전용) - main5.html 담당
# =========================================================
@app.post("/analyze-xml")
async def analyze_xml(file: UploadFile = File(...)):
    print(f">>> [LOG] MusicXML 분석 요청 수신: {file.filename}")
    try:
        content = await file.read()
        
        # XML 데이터 파싱 (제미나이를 거치지 않고 파이썬이 직접 100% 해독)
        root = ET.fromstring(content)
        melody_data = []
        current_time = 0.0
        
        for measure in root.findall('.//measure'):
            for note in measure.findall('note'):
                # 쉼표(rest) 건너뛰기
                if note.find('rest') is not None:
                    duration_node = note.find('duration')
                    if duration_node is not None:
                        current_time += float(duration_node.text) * 0.25 
                    continue
                
                # 음정(pitch) 추출
                pitch = note.find('pitch')
                if pitch is not None:
                    step = pitch.find('step').text 
                    octave = pitch.find('octave').text 
                    note_name = f"{step}{octave}"
                    
                    # 변화표(샵, 플랫) 확인
                    alter = pitch.find('alter')
                    if alter is not None:
                        if alter.text == '1':
                            note_name = f"{step}#{octave}"
                        elif alter.text == '-1':
                            note_name = f"{step}b{octave}"
                    
                    # 박자(duration) 추출
                    type_node = note.find('type')
                    duration_str = "4n" 
                    if type_node is not None:
                        type_val = type_node.text
                        if type_val == 'whole': duration_str = '1n'
                        elif type_val == 'half': duration_str = '2n'
                        elif type_val == 'quarter': duration_str = '4n'
                        elif type_val == 'eighth': duration_str = '8n'
                        elif type_val == '16th': duration_str = '16n'
                    
                    # 배열에 저장
                    melody_data.append({
                        "note": note_name,
                        "duration": duration_str,
                        "time": f"+{current_time}"
                    })
                    
                    # 다음 음표를 위해 시간 진행
                    current_time += 0.5 if duration_str == '8n' else 1.0

        print(f">>> [LOG] MusicXML 파싱 성공! 추출된 음표 수: {len(melody_data)}개")
        return {"melody": melody_data}

    except Exception as e:
        print(f">>> [ERROR] MusicXML 파싱 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"XML 분석 오류: {str(e)}")


