import os
import json
import io
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from google import genai
from PIL import Image

app = FastAPI()

# 디자인 지침에 따라 모든 접속을 허용합니다. [cite: 2026-02-11]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "노엘의 찬양노트 1.5-Flash 서버 가동 중!"}

# 정식 v1 채널 설정을 유지합니다. [cite: 2026-02-11]
client = genai.Client(
    api_key=os.getenv("APP_AI_KEY"),
    http_options={'api_version': 'v1'}
)

@app.post("/analyze-sheet")
async def analyze_sheet(file: UploadFile = File(...)):
    print(">>> [LOG] 악보 분석을 다시 시작합니다 (1.5-Flash)!")
    try:
        content = await file.read()
        img = Image.open(io.BytesIO(content))
        
        # 모델을 1.5-flash로 변경하여 할당량 문제를 해결합니다.
        response = client.models.generate_content(
            model='gemini-1.5-flash', 
            contents=[
                img, 
                "이 악보를 분석해서 {melody: [{note: 'C4', duration: '4n', time: '0:0:0'}]} 형식의 JSON 데이터만 출력해줘. 다른 텍스트는 제외해."
            ]
        )
        
        clean_json = response.text.replace('```json', '').replace('```', '').strip()
        print(">>> [LOG] 분석 성공!")
        return json.loads(clean_json)

    except Exception as e:
        print(f">>> [ERROR] 발생 상세: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

