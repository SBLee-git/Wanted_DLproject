from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends
from pydantic import BaseModel
from service.deep_diary import ChatbotService
import sys
import os
import shutil

# FastAPI 앱 생성
app = FastAPI()

# 챗봇 서비스 인스턴스 생성
chatbot = ChatbotService()
UPLOAD_DIR = "./uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ✅ 1️⃣ 이미지 캡션 생성 (URL 또는 파일)
@app.post("/generate_caption")
async def generate_caption(
    img_url: str = Form(None),  # URL 입력 가능
    file: UploadFile = File(None)  # 파일 업로드 가능
):
    """
    이미지 URL 또는 업로드된 파일을 받아 LLaVA 모델로 캡션을 생성하는 API
    """
    try:
        # 입력값 검증 (둘 다 없거나, 둘 다 있으면 오류)
        if not img_url and not file:
            raise HTTPException(status_code=400, detail="URL 또는 파일 중 하나를 제공해야 합니다.")
        if img_url and file:
            raise HTTPException(status_code=400, detail="URL과 파일 중 하나만 제공해야 합니다.")

        # 파일 업로드 처리
        if file:
            file_path = os.path.join(UPLOAD_DIR, file.filename)
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            image_source = file_path
            is_file = True
        else:
            image_source = img_url
            is_file = False

        # 캡션 생성
        caption = chatbot.generate_image_caption(image_source, is_file)
        return {"caption": caption}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ✅ 2️⃣ 첫 번째 질문 생성 (GET)
@app.get("/initial_question")
async def initial_question():
    """
    이전에 생성된 이미지 캡션을 기반으로 첫 번째 질문을 반환하는 API
    """
    try:
        question = chatbot.generate_initial_question()
        return {"question": question}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ✅ 3️⃣ 사용자 답변 후 후속 질문 생성 (POST)
class UserAnswerRequest(BaseModel):
    user_answer: str

@app.post("/followup_question")
async def followup_question(request: UserAnswerRequest):
    """
    사용자 답변을 입력받아 후속 질문을 생성하는 API
    """
    try:
        followup_question = chatbot.generate_followup_question(request.user_answer)
        return {
            "user_answer": request.user_answer,
            "emotion": chatbot.emotion_history[-1],
            "followup_question": followup_question
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ✅ 4️⃣ 대화 요약 및 감정 분석 (GET)
@app.get("/summarize_conversation")
async def summarize_conversation():
    """
    현재까지의 대화 내용을 요약하고, 최종 감정을 분석하는 API
    """
    try:
        chatbot.summarize_conversation()
        return {
            "diary_summary": chatbot.diary_summary,
            "final_emotion": chatbot.emotion_history[-1]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ✅ 5️⃣ 트로트 추천 (GET)
@app.get("/recommend_song")
async def recommend_song():
    """
    사용자의 감정과 대화 요약을 기반으로 트로트 가사를 추천하는 API
    """
    try:
        recommend_info = chatbot.recommend_song()
        return {"recommended_song": recommend_info}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



