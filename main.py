import os
import json
import io
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from google import genai  # 최신 라이브러리 사용
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
    return {"message": "노엘의 찬양노트 정식 서버(v1) 가동 중!"}

# [핵심] 정식 버전(v1)을 사용하도록 강제 설정합니다.
client = genai.Client(
    api_key=os.getenv("APP_AI_KEY"),
    http_options={'api_version': 'v1'}
)

@app.post("/analyze-sheet")
async def analyze_sheet(file: UploadFile = File(...)):
    try:
        content = await file.read()
        img = Image.open(io.BytesIO(content))
        
        # 404 에러를 피하기 위해 가장 표준적인 모델명을 사용합니다.
        response = client.models.generate_content(
            model='gemini-1.5-flash', 
            contents=[img, "이 악보를 분석해서 {melody: [{note: 'C4', duration: '4n', time: '0:0:0'}]} 형식의 JSON 데이터만 출력해줘."]
        )
        
        clean_json = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(clean_json)

    except Exception as e:
        print(f"Error detail: {str(e)}")
        raise HTTPException(status_code=500, detail=f"분석 실패: {str(e)}")



