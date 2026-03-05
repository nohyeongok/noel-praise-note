import os
import json
import io
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai
from PIL import Image

app = FastAPI()

# [cite: 2026-02-11] 이 세 가지 설정이 모두 있어야 브라우저 차단이 풀립니다.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://noelnote.kr",
        "https://www.noelnote.kr",
        "http://noelnote.kr",
        "http://www.noelnote.kr"
    ],
    allow_credentials=True,
    allow_methods=["*"],  # ✅ 필수: 모든 접속 방식(POST 등) 허용
    allow_headers=["*"],  # ✅ 필수: 모든 서류 양식(Header) 허용
)

@app.get("/")
async def root():
    return {"message": "노엘의 찬양노트 AI 서버가 준비되었습니다!"}

GOOGLE_API_KEY = os.getenv("APP_AI_KEY")
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

@app.post("/analyze-sheet")
async def analyze_sheet(file: UploadFile = File(...)):
    try:
        content = await file.read()
        img = Image.open(io.BytesIO(content))

        prompt = """
        이 악보 이미지를 분석해서 음악 데이터를 추출해줘.
        결과는 반드시 아래의 JSON 형식으로만 대답해:
        {
            "melody": [
                {"note": "C4", "duration": "4n", "time": "0:0:0"},
                ...
            ]
        }
        """
        response = model.generate_content([prompt, img])
        clean_json = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(clean_json)
    except Exception as e:
        # 에러 발생 시 로그를 찍어 확인을 돕습니다.
        print(f"Error detail: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
