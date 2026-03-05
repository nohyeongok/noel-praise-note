import os
import json
import io
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai
from PIL import Image

app = FastAPI()

# 1. 보안(CORS) 설정: 홈페이지의 접근을 허용합니다. [cite: 2026-02-11]
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://noelnote.kr", "https://www.noelnote.kr",
        "http://noelnote.kr", "http://www.noelnote.kr"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. 서버 연결 확인용 (브라우저에서 보이는 메시지)
@app.get("/")
async def root():
    return {"message": "노엘의 찬양노트 AI 서버가 준비되었습니다!"}

# 3. 제미나이 AI 설정 [cite: 2026-02-11]
# Render의 Environment에 넣은 'APP_AI_KEY'를 가져와서 사용합니다.
APP_AI_KEY = os.getenv("APP_AI_KEY")
genai.configure(api_key=APP_AI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# 4. 핵심 기능: 악보 분석 (이 부분이 404 에러의 원인이었습니다!) [cite: 2026-02-11]
@app.post("/analyze-sheet")
async def analyze_sheet(file: UploadFile = File(...)):
    try:
        content = await file.read()
        img = Image.open(io.BytesIO(content))

        prompt = """
        이 악보 이미지를 분석해서 멜로디 데이터를 추출해줘.
        결과는 반드시 아래의 JSON 형식으로만 대답해:
        {
            "melody": [
                {"note": "C4", "duration": "4n", "time": "0:0:0"},
                ...
            ]
        }
        """
        response = model.generate_content([prompt, img])
        
        # AI 응답에서 JSON만 추출
        clean_json = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(clean_json)
    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
