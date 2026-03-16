from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import requests  # 닷홈 PHP와 통신하기 위해 필요합니다
import google.generativeai as genai

app = FastAPI()

# 1. CORS 설정: noelnote.kr 관련 모든 도메인 허용
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

# 2. Gemini AI 설정 (Gemini 2.5 Flash 적용)
GENAI_API_KEY = os.getenv("GENAI_API_KEY")
genai.configure(api_key=GENAI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

# 📍 3. 닷홈 PHP 다리 주소 (목사님의 실제 파일 경로로 확인해 주세요)
# 예: https://noelnote.kr/api_bridge.php 또는 https://noelnote.kr/bible-ai/api_bridge.php
PHP_BRIDGE_URL = "https://noelnote.kr/bible-ai/api_bridge.php"

# 4. 구속사적 관점 시스템 프롬프트
SYSTEM_PROMPT = """
당신은 성경을 '구속사적 관점(Redemptive-Historical Perspective)'으로 해석하는 신학 전문가입니다.
모든 답변은 다음 원칙을 반드시 따릅니다:

1. 성경의 사건과 인물을 예수 그리스도를 통한 하나님의 구원 계획으로 연결하여 설명하십시오.
2. 도덕적 훈계를 넘어 복음의 핵심(은혜, 대속, 완성)을 깊이 있게 다루십시오.
3. 답변의 맨 마지막 줄에는 반드시 [CARD]라는 태그를 붙이고, 전체 내용을 암기하기 좋게 한 줄로 '요약'하십시오.
4. 요약문 안에는 반드시 핵심 성경 구절을 **(성경책 장:절)** 형식으로 '굵게' 포함하십시오.
5. 마지막에 [CATEGORY] 태그를 붙이고 '언약/시대/권별' 기준으로 카테고리를 생성하세요. (예: 구약/언약/창세기)

예시: [본문 설명...] [CARD] 요약문 **(구절)** [CATEGORY] 구약/언약/창세기
"""

# 데이터 모델 정의
class ChatRequest(BaseModel):
    message: str

class SaveRequest(BaseModel):
    question: str
    answer: str
    card: str
    category: str

# [기능 1] AI 질문하기 (상담 기능)
@app.post("/ask")
async def ask_bible_ai(request: ChatRequest):
    try:
        prompt = f"{SYSTEM_PROMPT}\n\n사용자 질문: {request.message}"
        response = model.generate_content(prompt)
        
        if not response.text:
            raise ValueError("AI가 답변을 생성하지 못했습니다.")
            
        return {"answer": response.text}
    except Exception as e:
        print(f"🚨 [AI 에러]: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# [기능 2] 게시판 저장하기 (PHP 다리를 통해 닷홈 DB로 전송)
@@app.post("/save")
async def save_to_db(req: SaveRequest):
    try:
        # 닷홈 PHP 호출
        response = requests.post(PHP_BRIDGE_URL, json=req.dict(), timeout=10)
        
        # ✨ 핵심 추가: 닷홈이 뭐라고 대답했는지 로그에 무조건 찍습니다.
        print(f"📡 닷홈 대답 상태코드: {response.status_code}")
        print(f"📡 닷홈 대답 내용: {response.text}")

        # 정상적인 JSON 응답인 경우에만 처리
        return response.json()
        
    except Exception as e:
        # 에러 내용을 더 구체적으로 찍어줍니다.
        error_msg = f"🚨 [저장 에러]: {str(e)}"
        print(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@app.get("/")
async def root():
    return {"status": "Noel Bible AI Bridge Mode is Online"}
