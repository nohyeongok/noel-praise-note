from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import google.generativeai as genai

app = FastAPI()

# 1. CORS 설정: noelnote.kr 관련 도메인 허용
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

# 2. Gemini AI 설정 (목사님이 성공하셨던 'gemini-2.5-flash' 모델 적용)
GENAI_API_KEY = os.getenv("GENAI_API_KEY")
genai.configure(api_key=GENAI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

# 3. 구속사적 관점 시스템 프롬프트
SYSTEM_PROMPT = """
당신은 성경을 '구속사적 관점(Redemptive-Historical Perspective)'으로 해석하는 신학 전문가입니다.
모든 답변은 다음 원칙을 따릅니다:
1. 성경의 모든 사건과 인물을 '예수 그리스도를 통한 하나님의 구원 계획'과 연결합니다.
2. 도덕적 교훈에 그치지 않고, 복음의 핵심(은혜, 대속, 완성)을 설명합니다.
3. 사용자가 이해하기 쉽게 설명하되, 신학적 깊이를 유지합니다.
4. 친절하고 따뜻한 목회자의 어조를 사용합니다.
"""

class ChatRequest(BaseModel):
    message: str

@app.post("/ask")
async def ask_bible_ai(request: ChatRequest):
    try:
        # 질문에 구속사적 맥락 결합
        prompt = f"{SYSTEM_PROMPT}\n\n사용자 질문: {request.message}"
        response = model.generate_content(prompt)
        
        if not response.text:
            raise ValueError("AI가 답변을 생성하지 못했습니다.")
            
        return {"answer": response.text}

    except Exception as e:
        # Render 로그에서 확인 가능하도록 에러 상세 출력
        print(f"🚨 [에러 발생 상세 내용]: {str(e)}") 
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    return {"status": "Noel Bible AI is online with Gemini 2.5 Flash"}
