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
    return {"message": "노엘의 찬양노트 최종 안정화 서버 가동 중!"}

# [핵심] 1.5 모델을 안정적으로 부르기 위해 v1beta 채널을 사용합니다.
client = genai.Client(
    api_key=os.getenv("APP_AI_KEY"),
    http_options={'api_version': 'v1beta'}
)

@app.post("/analyze-sheet")
async def analyze_sheet(file: UploadFile = File(...)):
    print(">>> [LOG] 악보 분석 시도 중...")
    try:
        content = await file.read()
        img = Image.open(io.BytesIO(content))
        
        # 무료 한도가 비교적 넉넉한 1.5-flash 모델을 사용합니다.
        response = client.models.generate_content(
            model='gemini-1.5-flash', 
            contents=[img, "이 악보를 분석해서 {melody: [{note: 'C4', duration: '4n', time: '0:0:0'}]} 형식의 JSON 데이터만 출력해줘."]
        )
        
        clean_json = response.text.replace('```json', '').replace('```', '').strip()
        print(">>> [LOG] 분석 성공!")
        return json.loads(clean_json)

    except Exception as e:
        # 에러 메시지를 목사님이 홈페이지에서 바로 보실 수 있게 상세히 전달합니다.
        error_msg = str(e)
        if "429" in error_msg:
            error_msg = "구글 AI가 바쁩니다. 1분만 기다렸다가 다시 시도해 주세요."
        print(f">>> [ERROR] 발생: {error_msg}")
        raise HTTPException(status_code=500, detail=error_msg)
