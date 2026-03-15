from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
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

# 3. 구속사적 관점 + 자동 카테고리 생성 지침
SYSTEM_PROMPT = """
당신은 성경을 '구속사적 관점'으로 해석하는 신학 전문가입니다.
모든 답변은 다음 형식을 반드시 따릅니다:

1. [본문]: 구속사적 맥락에서 상세히 설명하십시오.
2. [CARD]: 답변의 핵심 내용을 한 줄로 요약하고, 성경 구절을 **(장:절)** 형식으로 굵게 포함하세요.
3. [CATEGORY]: 해당 질문에 가장 적합한 카테고리를 '언약/시대/권별' 기준으로 생성하세요. 
   (예: 구약/언약/창세기, 신약/그리스도/로마서 등)
"""

class ChatRequest(BaseModel):
    message: str

@app.post("/ask")
async def ask_bible_ai(request: ChatRequest):
    try:
        prompt = f"{SYSTEM_PROMPT}\n\n사용자 질문: {request.message}"
        response = model.generate_content(prompt)
        
        if not response.text:
            raise ValueError("AI가 답변을 생성하지 못했습니다.")
            
        return {"answer": response.text}

    except Exception as e:
        print(f"🚨 [에러 발생]: {str(e)}") 
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    return {"status": "Noel Bible AI is online with Auto-Categorization"}
