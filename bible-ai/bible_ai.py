from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import requests
import google.generativeai as genai

app = FastAPI()

# 1. CORS 설정 (기존과 동일)
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

# 📍 3. 닷홈 PHP 다리 주소
PHP_BRIDGE_URL = "https://noelnote.kr/bible-ai/api_bridge.php"

# ✨ 4. 시스템 프롬프트 수정 (번호 표기 금지 명령 추가)
SYSTEM_PROMPT = """
당신은 성경을 '구속사적 관점(Redemptive-Historical Perspective)'으로 해석하는 신학 전문가입니다.
답변할 때 절대로 1., 2., 3. 같은 번호를 앞에 붙이지 마세요. 오직 아래의 [태그]만 사용하여 내용을 구분하세요.

- [본문] 태그 뒤에 성경의 사건과 그리스도를 연결하는 구속사적 상세 설명을 작성하세요.
- [CARD] 태그 뒤에 암기하기 좋은 한 줄 요약과 핵심 성경 구절을 **(성경책 장:절)** 형식으로 굵게 포함하세요.
- [CATEGORY] 태그 뒤에 '언약/시대/권별' 기준의 카테고리를 작성하세요.

※ 주의: 답변의 끝이나 암기 요약의 끝에 '2.', '3.', '**' 같은 불필요한 번호나 기호를 절대 남기지 마세요.
"""

class ChatRequest(BaseModel):
    message: str

class SaveRequest(BaseModel):
    question: str
    answer: str
    card: str
    category: str

@app.post("/ask")
async def ask_bible_ai(request: ChatRequest):
    try:
        # 지시문과 질문을 결합하여 전달
        prompt = f"{SYSTEM_PROMPT}\n\n사용자 질문: {request.message}"
        response = model.generate_content(prompt)
        return {"answer": response.text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/save")
async def save_to_db(req: SaveRequest):
    try:
        response = requests.post(PHP_BRIDGE_URL, json=req.dict(), timeout=10)
        return response.json()
    except Exception as e:
        print(f"🚨 저장 에러: {str(e)}")
        raise HTTPException(status_code=500, detail="닷홈 DB 연결 다리 응답 없음")

@app.get("/list")
async def get_list():
    try:
        response = requests.get(PHP_BRIDGE_URL, timeout=10)
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail="목록 불러오기 실패")

@app.get("/")
async def root():
    return {"status": "Noel Bible AI is Online"}
