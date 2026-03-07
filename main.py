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
    return {"message": "노엘의 찬양노트 US 서버 정상 가동 중!"}

# 가장 안정적인 기본 설정으로 돌아갑니다.
client = genai.Client(api_key=os.getenv("APP_AI_KEY"))

@app.post("/analyze-sheet")
async def analyze_sheet(file: UploadFile = File(...)):
    print(">>> [LOG] 악보 분석 시도 (2.0-Flash)")
    try:
        content = await file.read()
        img = Image.open(io.BytesIO(content))
        
        # 아까 구글과 연결에 성공했던 그 모델입니다.
        response = client.models.generate_content(
            model='gemini-2.0-flash', 
            contents=[img, "이 악보를 분석해서 {melody: [{note: 'C4', duration: '4n', time: '0:0:0'}]} 형식의 JSON 데이터만 출력해줘."]
        )
        
        clean_json = response.text.replace('```json', '').replace('```', '').strip()
        print(">>> [LOG] 분석 성공!")
        return json.loads(clean_json)

    except Exception as e:
        print(f">>> [ERROR] 발생 상세: {str(e)}")
        # 에러 메시지를 프론트엔드로 보내서 확인합니다.
        raise HTTPException(status_code=500, detail=str(e))

