import sys
import os

# 프로젝트 루트 디렉토리를 파이썬 경로에 추가
sys.path.append(os.path.abspath("."))

# Gemini API 관련 라이브러리 임포트
from config.api_keys import gemini_key
import google.generativeai as genai

class DiaryQuestionLLMService:
    """
    이미지 캡셔닝 결과(또는 사용자 답변)를 바탕으로
    LLM을 활용해 질문을 생성하고, 추가 질문을 만들어내는 기능을 담당하는 클래스.
    """

    def __init__(self):
        # Gemini API 설정
        genai.configure(api_key=gemini_key)
        # 사용할 모델 선택
        self.model = genai.GenerativeModel('gemini-2.0-flash')

        # 서비스 역할(지시문)
        self.role = "당신은 사용자가 일기를 편리하게 쓸 수 있도록 도와주는 서비스입니다."

        # 캡션(이미지에 대한 요약 정보) 보관
        self.caption = ""

        # 대화 내용 기록 (최대 10개 유지)
        self.conversation_history = []

    def set_caption(self, caption: str) -> None:
        """
        캡션 정보를 클래스 속성에 저장.
        """
        self.caption = caption.strip()

    def record_interaction(self, speaker: str, content: str) -> None:
        """
        대화 내용을 기록하는 메서드. 최대 10개까지만 저장.
        speaker는 'User' 또는 'AI'로 사용.
        """
        self.conversation_history.append(f"{speaker}: {content.strip()}")
        
        # 대화 기록이 10개를 초과하면 가장 오래된 항목 제거
        if len(self.conversation_history) > 10:
            self.conversation_history.pop(0)

    def generate_question_from_caption(self) -> str:
        """
        이미지 캡셔닝 결과(self.caption)를 바탕으로
        사용자에게 일기 작성에 도움이 될 만한 첫 번째 질문을 생성.
        """
        prompt = f"""
        캡셔닝 결과: {self.caption}
        요청사항: {self.role}
        사용자가 업로드한 이미지의 캡셔닝 결과를 바탕으로,
        이미지에서 일기에 쓸 만한 주제를 자연스럽게 한 줄로 언급하고,
        흥미롭고 답변하기 쉬운 한 가지 질문을 한글로 만들어주세요.
        """
        response = self.model.generate_content(prompt)
        ai_question = response.text.strip()

        # 대화 기록에 추가 (AI 발화)
        self.record_interaction("AI", ai_question)

        return ai_question

    def generate_followup_question(self, user_answer: str) -> str:
        """
        사용자의 이전 답변(user_answer)과 대화 기록(self.conversation_history)을 바탕으로,
        후속 질문을 생성하는 메서드.
        """
        # 사용자가 입력한 답변을 대화 기록에 추가 (User 발화)
        self.record_interaction("User", user_answer)

        # 대화 기록을 문자열로 변환
        history_text = "\n".join(self.conversation_history)

        prompt = f"""
        캡셔닝 결과: "{self.caption}"
        지금까지의 대화 기록:
        {history_text}

        요청사항: {self.role}
        위의 내용을 참고하여, 일기 작성을 좀 더 구체화하거나 흥미로운 이야기를 이끌어낼 수 있는 한 가지 후속 질문을 한글로 만들어주세요.
        주제가 반복되거나 사용자가 불편함을 느끼는 주제라고 판단될 경우 캡셔닝 결과 또는 대화 기록에서 새로운 주제를 찾으세요.
        """
        response = self.model.generate_content(prompt)
        ai_question = response.text.strip()

        # AI가 생성한 질문을 대화 기록에 추가
        self.record_interaction("AI", ai_question)

        return ai_question

    def generate_diary_draft(self) -> str:
        """
        지금까지 기록한 전체 대화 내용(self.conversation_history)을 요약하여,
        사용자가 작성할 일기 초안을 생성해주는 메서드.
        """
        # 대화 로그를 하나의 문자열로 합침
        full_conversation = "\n".join(self.conversation_history)

        prompt = f"""
        다음은 사용자와 서비스(당신) 간의 대화 내용입니다:
        {full_conversation}

        역할: {self.role}
        요청사항: 위 대화 내용을 바탕으로, 사용자 입장에서 쓸 수 있는 일기 초안을 한글로 작성해주세요.
        문맥과 감정을 담되, 이모지를 사용하지 않고, 간결하고 자연스러운 문장으로 요약하여 작성해주시기 바랍니다.
        """
        response = self.model.generate_content(prompt)
        diary_draft = response.text.strip()
        return diary_draft

# =================== 사용 예시 (인터랙티브) ===================

def main():
    # 테스트용 캡션
    test_caption = """
        In the image, a group of people is gathered around a dining table, enjoying a meal together.
        The table is filled with various food items, including a large grilled pork dish, a bowl of salad, and several bottles of beer.
        The atmosphere appears to be relaxed and social as the group shares a meal together.
    """

    # 1) 서비스 객체 생성
    service = DiaryQuestionLLMService()

    # 2) 캡션 설정
    service.set_caption(test_caption)

    # 3) 캡션을 바탕으로 첫 질문 생성
    initial_question = service.generate_question_from_caption()
    print("\nAI 질문:", initial_question)

    while True:
        # 4) 사용자 답변 받기
        user_answer = input("\n사용자 답변을 입력해주세요 (종료하려면 'exit' 입력): ").strip()

        # 종료 조건
        if user_answer.lower() == 'exit':
            print("\n대화를 종료합니다.")
            break

        # 5) 후속 질문 생성
        followup_question = service.generate_followup_question(user_answer)
        print("\nAI 후속 질문:", followup_question)

    # 6) 전체 대화를 기반으로 일기 초안 생성
    diary_draft = service.generate_diary_draft()
    print("\n===== 요약된 일기 초안 =====")
    print(diary_draft)

if __name__ == "__main__":
    main()
