from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import google.generativeai as genai
import mysql.connector # MySQL 연결 라이브러리

app = FastAPI()

# 1. CORS 설정
origins = ["https://noelnote.kr", "https://www.noelnote.kr", "http://localhost:3000"]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# 2. AI 설정
genai.configure(api_key=os.getenv("GENAI_API_KEY"))
model = genai.GenerativeModel('gemini-2.5-flash')

# 3. 닷홈 DB 연결 함수
def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host=os.getenv("112.175.185.138"),      # DB 서버 주소
            user=os.getenv("noelnote"),      # DB 아이디
            password=os.getenv("noel@1015shst"), # DB 비밀번호
            database=os.getenv("noelnote"),  # DB 이름
            charset='utf8mb4'
        )
        return conn
    except Exception as e:
        print(f"❌ DB 연결 실패: {e}")
        return None

SYSTEM_PROMPT = """당신은 구속사적 성경 전문가입니다. 
모든 답변 끝에 반드시 [CARD] 요약문 **(구절)** [CATEGORY] 카테고리 형식을 지키세요."""

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
        response = model.generate_content(f"{SYSTEM_PROMPT}\n\n질문: {request.message}")
        return {"answer": response.text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# [기능 2] 닷홈 DB에 저장하기
@app.post("/save")
async def save_to_db(req: SaveRequest):
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="DB 연결에 실패했습니다.")
    
    try:
        cursor = conn.cursor()
        sql = "INSERT INTO bible_board (question, answer, card, category) VALUES (%s, %s, %s, %s)"
        values = (req.question, req.answer, req.card, req.category)
        cursor.execute(sql, values)
        conn.commit()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()

# [기능 3] 게시판 목록 가져오기
@app.get("/list")
async def get_list():
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="DB 연결 실패")
    
    try:
        cursor = conn.cursor(dictionary=True) # 결과를 딕셔너리 형태로 가져옴
        cursor.execute("SELECT * FROM bible_board ORDER BY created_at DESC")
        rows = cursor.fetchall()
        return rows
    finally:
        cursor.close()
        conn.close()

@app.get("/")
async def root(): return {"status": "Dothome DB Board Engine Online"}
