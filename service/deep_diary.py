import sys
import os

# 프로젝트 루트 디렉토리를 파이썬 경로에 추가
sys.path.append(os.path.abspath("."))

from models.image_captioning import LlavaImageCaptioning
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
caption_generator = LlavaImageCaptioning()

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
        image = caption_generator.load_image_from_url(image_path)
        self.caption = caption_generator.generate_caption(image)
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

# =================== 사용 예시 (로그 & 터미널 동시 출력) ===================

class DualOutput:
    """
    표준 출력(sys.stdout)과 로그 파일 출력을 동시에 수행하는 클래스
    """
    def __init__(self, terminal, log_file):
        self.terminal = terminal  # 터미널 출력 (기본 sys.stdout)
        self.log_file = log_file  # 로그 파일 출력 스트림

    def write(self, message):
        self.terminal.write(message)  # 터미널에 출력
        self.log_file.write(message)  # 로그 파일에도 기록
        self.terminal.flush()
        self.log_file.flush()

    def flush(self):
        """
        Python의 출력 버퍼를 비우기 위한 메서드
        """
        self.terminal.flush()
        self.log_file.flush()


if __name__ == "__main__":
    from datetime import datetime
    
    # 로그 파일 경로 설정 (YYYYMMDD_log.txt 형식)
    log_filename = datetime.now().strftime("%Y%m%d") + "_log.txt"
    log_path = os.path.join("service/logs", log_filename)

    # 로그 파일 열기
    log_file = open(log_path, "a", encoding="utf-8")

    # 터미널 & 파일 동시에 출력하도록 변경
    sys.stdout = DualOutput(sys.stdout, log_file)

    print(f"{datetime.now().time()}, 로그 기록 시작: {log_path}\n")

    chatbot = ChatbotService()

    img_url = input("Enter the image URL: ").strip()
    print(img_url)
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

    print(f"\n✅ 로그 기록 완료: {log_path}\n\n\n")

    # 로그 파일 닫기
    log_file.close()