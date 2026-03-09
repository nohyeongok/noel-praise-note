import os
import json
import io
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from google import genai
from PIL import Image

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
    return {"message": "노엘의 찬양노트 'Tier 1' 최종 안정화 서버 가동 중!"}

# 목사님의 'Tier 1' API 키가 적용된 클라이언트입니다.
client = genai.Client(api_key=os.getenv("APP_AI_KEY"))

@app.post("/analyze-sheet")
async def analyze_sheet(file: UploadFile = File(...)):
    print(">>> [LOG] 악보 분석 요청 수신 (Tier 1 최종 모드)")
    try:
        content = await file.read()
        img = Image.open(io.BytesIO(content))
        
        # 유료 등급에서 가장 안정적으로 작동하는 모델명입니다. [cite: 2026-02-11]
        response = client.models.generate_content(
            model='gemini-1.5-flash', 
            contents=[
                img, 
                "이 악보를 분석해서 {melody: [{note: 'C4', duration: '4n', time: '0:0:0'}]} 형식의 JSON 데이터만 출력해줘."
            ]
        )
        
        clean_json = response.text.replace('```json', '').replace('```', '').strip()
        print(">>> [LOG] 분석 성공!")
        return json.loads(clean_json)

    except Exception as e:
        # 에러 발생 시 로그에 상세 정보를 남겨 목사님을 돕겠습니다. [cite: 2026-03-09]
        print(f">>> [ERROR] 상세: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
