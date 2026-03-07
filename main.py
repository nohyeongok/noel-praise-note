import os
import json
import io
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from google import genai
from PIL import Image

app = FastAPI()

# 목사님의 레이아웃 지침을 준수하며 모든 접속을 허용합니다. [cite: 2026-02-11]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "노엘의 찬양노트 US 서버가 깨끗하게 가동 중입니다!"}

# [필수] 구글이 권장하는 최신 무전기(v1 정식 채널) 설정입니다.
client = genai.Client(
    api_key=os.getenv("APP_AI_KEY"),
    http_options={'api_version': 'v1'}
)

@app.post("/analyze-sheet")
async def analyze_sheet(file: UploadFile = File(...)):
    print(">>> [LOG] 새로운 악보 분석을 시작합니다!")
    try:
        content = await file.read()
        img = Image.open(io.BytesIO(content))
        
        # 가장 안정적인 정식 모델을 호출합니다.
        response = client.models.generate_content(
            model='gemini-1.5-flash', 
            contents=[img, "이 악보를 분석해서 {melody: [{note: 'C4', duration: '4n', time: '0:0:0'}]} 형식의 JSON 데이터만 출력해줘."]
        )
        
        clean_json = response.text.replace('```json', '').replace('```', '').strip()
        print(">>> [LOG] 분석에 성공했습니다!")
        return json.loads(clean_json)

    except Exception as e:
        print(f">>> [ERROR] 발생: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
