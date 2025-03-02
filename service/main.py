from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from service.deep_diary import ChatbotService
import sys
import os

# FastAPI 앱 생성
app = FastAPI()

# 챗봇 서비스 인스턴스 생성
chatbot = ChatbotService()


# ✅ 1️⃣ 이미지 캡션 생성 (POST)
class ImageRequest(BaseModel):
    img_url: str

@app.post("/generate_caption")
async def generate_caption(request: ImageRequest):
    """
    이미지 URL을 받아 LLaVA 모델로 캡션을 생성하는 API
    """
    try:
        caption = chatbot.generate_image_caption(request.img_url)
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



