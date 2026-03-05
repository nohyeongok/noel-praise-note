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
    allow_origins=[
        "https://noelnote.kr", "https://www.noelnote.kr",
        "http://noelnote.kr", "http://www.noelnote.kr"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "노엘의 찬양노트 AI 서버가 준비되었습니다!"}

APP_AI_KEY = os.getenv("APP_AI_KEY")
client = genai.Client(api_key=APP_AI_KEY)

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
                {"note": "C4", "duration": "4n", "time": "0:0:0"}
            ]
        }
        """
        
        # [여기 집중!] 서버가 절대 딴소리 못하게 2.0-flash로 고정했습니다.
        response = client.models.generate_content(
            model='gemini-1.5-flash-latest',
            contents=[img, prompt]
        )
        
        clean_json = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(clean_json)

    except Exception as e:
        print(f"Error detail: {str(e)}")
        raise HTTPException(status_code=500, detail="악보 분석 중 오류가 발생했습니다.")





