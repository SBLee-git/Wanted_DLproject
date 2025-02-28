import sys
import os

# 프로젝트 루트 디렉토리를 파이썬 경로에 추가
sys.path.append(os.path.abspath("."))

from models.image_captioning import generate_image_caption
from models.llm_gemini import generate_question_from_caption, generate_followup_question, generate_diary_draft
# from models.emotion_analysis import analyze_emotion
def analyze_emotion(text):
    return "무난"
# from models.recommendation import recommend_activity, recommend_product
def recommend_activity(text):
    return "산책"
def recommend_product(text):
    return "술"
# from models.insights import generate_insights

class ChatbotService:
    """
    챗봇 서비스 클래스:
    - 이미지 캡셔닝
    - 챗봇 대화(질문 생성, 감정 분석)
    - 일기 초안 생성
    - 추천 기능(활동, 상품)
    - 감정 분석 기반 인사이트 제공
    """

    def __init__(self):
        self.caption = ""  # 이미지 캡션 저장
        self.conversation_history = []  # 대화 기록
        self.emotion_history = []  # 감정 기록 (사용자 감정 분류 데이터)

    def record_interaction(self, speaker: str, content: str) -> None:
        """
        대화 내용을 기록
        """
        self.conversation_history.append(f"{speaker}: {content.strip()}")
        
        if len(self.conversation_history) > 20:  # 최대 20개
            self.conversation_history.pop(0)

    def generate_image_caption(self, image_path: str) -> str:
        """
        이미지 캡션 생성
        """
        self.caption = generate_image_caption(image_path)
        return self.caption

    def generate_initial_question(self) -> str:
        """
        이미지 캡셔닝 결과를 기반으로 첫 번째 질문 생성
        """
        if not self.caption:
            raise ValueError("캡션이 설정되지 않았습니다. 먼저 이미지 캡션을 생성하세요.")

        initial_question = generate_question_from_caption(self.caption)
        self.record_interaction("AI", initial_question)
        return initial_question

    def generate_followup_question(self, user_answer: str) -> str:
        """
        사용자의 답변을 바탕으로 후속 질문을 생성
        """
        self.record_interaction("User", user_answer)

        # 감정 분석
        emotion_result = analyze_emotion(user_answer)
        self.emotion_history.append(emotion_result)

        # 후속 질문 생성
        followup_question = generate_followup_question(self.conversation_history, self.caption)
        self.record_interaction("AI", followup_question)

        return followup_question

    def generate_diary_draft(self) -> str:
        """
        대화 내용을 기반으로 일기 초안을 생성
        """
        return generate_diary_draft(self.conversation_history)

    def recommend_activity(self) -> str:
        """
        감정 분석 결과를 기반으로 활동을 추천
        """
        if not self.emotion_history:
            return "아직 감정 데이터를 분석하지 않았습니다."
        latest_emotion = self.emotion_history[-1]
        return recommend_activity(latest_emotion)

    def recommend_product(self) -> str:
        """
        감정 분석 결과 및 일기 내용을 기반으로 상품을 추천
        """
        if not self.emotion_history:
            return "아직 감정 데이터를 분석하지 않았습니다."
        latest_emotion = self.emotion_history[-1]
        return recommend_product(latest_emotion)

# =================== 사용 예시 ===================

if __name__ == "__main__":
    chatbot = ChatbotService()

    img_url = input("Enter the image URL: ").strip()
    caption = chatbot.generate_image_caption(img_url)
    print("\n📷 이미지 캡션 생성:", caption)

    initial_question = chatbot.generate_initial_question()
    print("\n🤖 AI:", initial_question)

    while True:
        user_answer = input("\n👤 사용자 답변 (종료하려면 'exit' 입력): ").strip()
        print("\n🙂 User:", user_answer)
        if user_answer.lower() == "exit":
            print("\n💡 대화를 종료합니다.")
            break

        followup_question = chatbot.generate_followup_question(user_answer)
        print("\n🤖 AI:", followup_question)

    diary_draft = chatbot.generate_diary_draft()
    print("\n📖 일기 초안:\n", diary_draft)
