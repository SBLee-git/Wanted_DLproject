from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Request, Response, Cookie
from pydantic import BaseModel
from service.deep_diary import ChatbotService
import os
import shutil
import uuid

app = FastAPI()

# 서버 실행 중 클라이언트별 챗봇 세션을 관리하는 딕셔너리
active_sessions = {}

def get_or_create_client_id(request: Request, response: Response) -> str:
    """쿠키에서 `client_id` 확인하고 없으면 새로 생성하여 쿠키에 저장"""
    client_id = request.cookies.get("client_id")
    print("client_id:", client_id)
    if not client_id:
        client_id = str(uuid.uuid4())  # 새로운 client_id 생성
        response.set_cookie(key="client_id", value=client_id, httponly=True, max_age=86400)  # 하루 유지
    return client_id

def get_chatbot(client_id: str) -> ChatbotService:
    """클라이언트별 `ChatbotService` 인스턴스를 유지"""
    if client_id not in active_sessions:
        active_sessions[client_id] = ChatbotService(session_id=client_id)
    return active_sessions[client_id]

class UserAnswerRequest(BaseModel):
    user_answer: str

class DiaryUpdateRequest(BaseModel):
    user_changes: str


# 이미지 캡션 생성 (세션 자동 관리)
@app.post("/generate_caption")
async def generate_caption(
    request: Request,
    response: Response,
    img_url: str = Form(None),
    file: UploadFile = File(None),
):
    """이미지 URL 또는 파일을 받아 캡션을 생성하고 세션 ID를 자동 관리"""
    client_id = get_or_create_client_id(request, response)
    chatbot = get_chatbot(client_id)

    # 클라이언트별 세션 경로 사용
    session_path = chatbot.session_path
    os.makedirs(session_path, exist_ok=True)

    if file:
        file_path = os.path.join(session_path, file.filename)
        with open(file_path, "wb") as buffer:
            buffer.write(await file.read())
        image_source, is_file = file_path, True
    elif img_url:
        image_source, is_file = img_url, False
    else:
        raise HTTPException(status_code=400, detail="URL 또는 파일 중 하나를 제공해야 합니다.")

    caption = chatbot.generate_image_caption(image_source, is_file)
    return {"client_id": client_id, "caption": caption}

# 첫 번째 질문 생성
@app.get("/initial_question")
async def initial_question(request: Request, response: Response):
    """클라이언트별 세션을 유지하면서 첫 번째 질문을 반환"""
    client_id = get_or_create_client_id(request, response)
    chatbot = get_chatbot(client_id)

    question = chatbot.generate_initial_question()
    return {"client_id": client_id, "question": question}

# 후속 질문 생성
@app.post("/followup_question")
async def followup_question(request: Request, response: Response, data: UserAnswerRequest):
    """사용자의 답변을 기반으로 후속 질문을 생성"""
    client_id = get_or_create_client_id(request, response)
    chatbot = get_chatbot(client_id)

    followup_question = chatbot.generate_followup_question(data.user_answer)
    return {
        "client_id": client_id,
        "user_answer": data.user_answer,
        "emotion": chatbot.emotion_history[-1],
        "followup_question": followup_question,
    }

# 대화 요약 및 감정 분석
@app.get("/summarize_conversation")
async def summarize_conversation(request: Request, response: Response):
    """클라이언트별 대화 내용을 요약하고 감정을 분석"""
    client_id = get_or_create_client_id(request, response)
    chatbot = get_chatbot(client_id)
    chatbot.summarize_conversation()
    return {
        "client_id": client_id,
        "diary_summary": chatbot.diary_summary,
        "final_emotion": chatbot.emotion_history[-1]
    }

# 일기 초안 재생성 (사용자 변경 반영)
@app.post("/regenerate_summarize")
async def regenerate_summarize(request: Request, response: Response, data: DiaryUpdateRequest):
    """사용자의 의견을 반영하여 일기 초안을 새로 생성"""
    client_id = get_or_create_client_id(request, response)
    chatbot = get_chatbot(client_id)
    chatbot.regenerate_summarize(data.user_changes)
    return {
        "client_id": client_id,
        "diary_summary": chatbot.diary_summary,
        "final_emotion": chatbot.emotion_history[-1]
    }
    
# 트로트 추천
@app.get("/recommend_song")
async def recommend_song(request: Request, response: Response):
    """클라이언트별 감정을 기반으로 트로트 가사를 추천"""
    client_id = get_or_create_client_id(request, response)
    chatbot = get_chatbot(client_id)

    recommended_song = chatbot.recommend_song()
    return {"client_id": client_id, "recommended_song": recommended_song}


@app.get("/save_diary")
async def save_diary(request: Request, response: Response):
    """대화내용 저장"""
    client_id = get_or_create_client_id(request, response)
    chatbot = get_chatbot(client_id)
    chatbot.save_diary()
    return {"client_id": client_id}
