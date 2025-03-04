import sys
import os

# 프로젝트 루트 디렉토리를 파이썬 경로에 추가
sys.path.append(os.path.abspath("."))

import json
from models.llm_gemini import generate_question_from_caption, generate_followup_question, generate_diary_draft, incorporate_user_changes
from models.image_captioning import LlavaImageCaptioning
from models.emotion_classification import EmotionClassifier
from models.semantic_embedding import E5Embedder, SongRecommender
# from models.insights import generate_insights

caption_generator = LlavaImageCaptioning()
emotion_classifier = EmotionClassifier()
embedder = E5Embedder()
song_recommander = SongRecommender()


class ChatbotService:
    """
    챗봇 서비스 클래스:
    - 이미지 캡셔닝
    - 챗봇 대화(질문 생성, 감정 분석)
    - 일기 초안 생성
    - 추천 기능(활동, 상품)
    - 감정 분석 기반 인사이트 제공
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.session_path = os.path.join("service/logs", session_id)
        os.makedirs(self.session_path, exist_ok=True)
        
        self.caption = ""  # 이미지 캡션 저장
        self.conversation_history = []  # 대화 기록
        self.emotion_history = []  # 감정 기록 (사용자 감정 분류 데이터)
        self.diary_summary = ""

    def record_interaction(self, speaker: str, content: str) -> None:
        """
        대화 내용을 기록
        """
        self.conversation_history.append(f"{speaker}: {content.strip()}")
        
        if len(self.conversation_history) > 20:  # 최대 20개
            self.conversation_history.pop(0)

    def generate_image_caption(self, image_source: str, is_file: bool = False) -> str:
        """
        이미지 캡션 생성 (URL 및 파일 지원)

        Args:
            image_source (str): 이미지 URL 또는 파일 경로
            is_file (bool): True이면 파일에서 로드, False이면 URL에서 로드 (기본값: False)

        Returns:
            str: 생성된 이미지 캡션
        """
        if is_file:
            image = caption_generator.load_image_from_file(image_source)
        else:
            image = caption_generator.load_image_from_url(image_source)

        if image is None:
            raise ValueError("이미지를 불러올 수 없습니다. URL 또는 파일 경로를 확인하세요.")

        self.caption, _ = caption_generator.generate_caption(image)
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
        emotion_result = emotion_classifier.predict_emotion(user_answer)
        self.emotion_history.append(emotion_result)

        # 후속 질문 생성
        followup_question = generate_followup_question(self.conversation_history, self.caption)
        self.record_interaction("AI", followup_question)

        return followup_question

    def summarize_conversation(self) -> str:
        """
        일기 초안을 위한 대화 내용 요약
        """
        summary = generate_diary_draft(self.conversation_history)
        total_emotion = emotion_classifier.predict_emotion(summary)
        self.emotion_history.append(total_emotion)
        self.diary_summary = summary
        return
    
    def regenerate_summarize(self, user_changes) -> str:
        """
        사용자의 의견을 반영한 일기 초안 새로 생성
        """
        summary_new = incorporate_user_changes(original_draft=self.diary_summary, user_changes=user_changes)
        total_emotion = emotion_classifier.predict_emotion(summary_new)
        self.emotion_history.append(total_emotion)
        self.diary_summary = summary_new
        return
    
    def save_diary(self, diary: str="") -> str:
        """
        사용자 작성 일기 저장
        """
        self.diary = diary
        self.save_conversation()
        return
    
    def save_conversation(self):
        """대화 내역을 JSON 파일로 저장"""
        file_path = os.path.join(self.session_path, "conversation.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump({
                "conversation": self.conversation_history,
                "emotion_history": self.emotion_history,
                "diary_summary": self.diary_summary,
                "diary": self.diary
            }, f, ensure_ascii=False, indent=4)

    def recommend_song(self) -> str:
        """
        감정 분석 결과를 기반으로 노래를 추천
        """
        if not self.emotion_history:
            return "아직 감정 데이터를 분석하지 않았습니다."
        final_emotion = self.emotion_history[-1]
        text = self.diary_summary
        embedding = embedder.get_embedding(text)
        recommend_info = song_recommander.recommend_song(embedding, final_emotion)
        print(recommend_info)
        return recommend_info


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
        print("emotion:", chatbot.emotion_history[-1])
        print("\n🤖 AI:", followup_question)

    chatbot.summarize_conversation()
    print("\n📖 일기 초안:\n", chatbot.diary_summary)
    print("final emotion:", chatbot.emotion_history[-1])
    
    recommend_info = chatbot.recommend_song()
    print("트로트 추천:\n", recommend_info)

    print(f"\n✅ 로그 기록 완료: {log_path}\n\n\n")

    # 로그 파일 닫기
    log_file.close()
    