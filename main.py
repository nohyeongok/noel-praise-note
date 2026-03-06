import os
import json
import io
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai
from PIL import Image

app = FastAPI()

# 목사님이 요청하신 중앙 정렬 및 디자인 최적화를 위해 모든 접속을 허용합니다. [cite: 2026-02-11]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "노엘의 찬양노트 표준 서버가 정상 작동 중입니다!"}

# 안정적인 표준 라이브러리 설정
genai.configure(api_key=os.getenv("APP_AI_KEY"))

@app.post("/analyze-sheet")
async def analyze_sheet(file: UploadFile = File(...)):
    try:
        content = await file.read()
        img = Image.open(io.BytesIO(content))
        
        # 404 에러를 피하기 위해 가장 최신의 안정적인 모델명을 사용합니다.
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        
        prompt = "이 악보를 분석해서 {melody: [{note: 'C4', duration: '4n', time: '0:0:0'}]} 형식의 JSON 데이터만 출력해줘."
        
        # 표준 방식으로 콘텐츠 생성 시도
        response = model.generate_content([img, prompt])
        
        # 결과값에서 JSON 텍스트만 추출
        clean_json = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(clean_json)

    except Exception as e:
        print(f"Error detail: {str(e)}")
        # 에러 발생 시 로그에 상세 내용을 남깁니다.
        raise HTTPException(status_code=500, detail=f"분석 실패: {str(e)}")


