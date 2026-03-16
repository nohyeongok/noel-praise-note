from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import requests
import google.generativeai as genai

app = FastAPI()

# 1. CORS 설정
origins = [
    "https://noelnote.kr",
    "https://www.noelnote.kr",
    "http://noelnote.kr",
    "http://www.noelnote.kr",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Gemini AI 설정
GENAI_API_KEY = os.getenv("GENAI_API_KEY")
genai.configure(api_key=GENAI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

# 📍 3. 닷홈 PHP 다리 주소 (파일 경로가 정확한지 다시 한번 확인!)
PHP_BRIDGE_URL = "https://noelnote.kr/bible-ai/api_bridge.php"

# 4. 시스템 프롬프트
SYSTEM_PROMPT = """
당신은 성경을 '구속사적 관점'으로 해석하는 신학 전문가입니다.
모든 답변은 다음 형식을 따릅니다:
1. [본문]: 상세 설명
2. [CARD]: 암기용 한 줄 요약 및 성경 구절 **(장:절)** 굵게 표시
3. [CATEGORY]: 언약/시대/권별 카테고리 생성
"""

class ChatRequest(BaseModel):
    message: str

class SaveRequest(BaseModel):
    question: str
    answer: str
    card: str
    category: str

# [기능 1] AI 질문하기
@app.post("/ask")
async def ask_bible_ai(request: ChatRequest):
    try:
        prompt = f"{SYSTEM_PROMPT}\n\n질문: {request.message}"
        response = model.generate_content(prompt)
        return {"answer": response.text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# [기능 2] 게시판 저장하기 (PHP 다리 호출)
@app.post("/save")
async def save_to_db(req: SaveRequest):
    try:
        # 닷홈 PHP 호출
        response = requests.post(PHP_BRIDGE_URL, json=req.dict(), timeout=10)
        
        # 로그 확인용 (Render 로그에서 확인 가능)
        print(f"📡 닷홈 대답 상태코드: {response.status_code}")
        print(f"📡 닷홈 대답 내용: {response.text}")

        return response.json()
    except Exception as e:
        print(f"🚨 [저장 에러]: {str(e)}")
        raise HTTPException(status_code=500, detail="닷홈 DB 연결 다리(PHP) 응답 오류")

# [기능 3] 게시판 목록 가져오기
@app.get("/list")
async def get_list():
    try:
        response = requests.get(PHP_BRIDGE_URL, timeout=10)
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail="목록 불러오기 실패")

@app.get("/")
async def root():
    return {"status": "Bridge Mode is Active"}
