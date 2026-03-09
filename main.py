import os
import json
import io
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from google import genai
from google.genai import types  # 정식 통로 설정을 위해 필요합니다.
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
    return {"message": "노엘의 찬양노트 'Tier 1' 정식 통로 연결 성공!"}

# 'v1' 정식 버전을 사용하도록 설정하여 404 에러를 방지합니다. [cite: 2026-02-11]
client = genai.Client(
    api_key=os.getenv("APP_AI_KEY"),
    http_options=types.HttpOptions(api_version='v1')
)

@app.post("/analyze-sheet")
async def analyze_sheet(file: UploadFile = File(...)):
    print(">>> [LOG] 악보 분석 요청 수신 (Tier 1 정식 통로)")
    try:
        content = await file.read()
        img = Image.open(io.BytesIO(content))
        
        # 가장 표준적인 gemini-1.5-flash 모델을 호출합니다. [cite: 2026-02-11]
        response = client.models.generate_content(
            model='gemini-1.5-flash', 
            contents=[
                img, 
                "이 악보를 분석해서 {melody: [{note: 'C4', duration: '4n', time: '0:0:0'}]} 형식의 JSON 데이터만 출력해줘."
            ]
        )
        
        if not response.text:
            raise ValueError("AI로부터 응답을 받지 못했습니다.")

        clean_json = response.text.replace('```json', '').replace('```', '').strip()
        print(">>> [LOG] 분석 성공!")
        return json.loads(clean_json)

    except Exception as e:
        error_msg = str(e)
        print(f">>> [ERROR] 상세 발생: {error_msg}")
        raise HTTPException(status_code=500, detail=error_msg)
