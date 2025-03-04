import sys
import os

# 프로젝트 루트 디렉토리를 파이썬 경로에 추가
sys.path.append(os.path.abspath("."))

# Gemini API 관련 라이브러리 임포트
from config.api_keys import gemini_key
import google.generativeai as genai

# Gemini API 설정
genai.configure(api_key=gemini_key)

# 사용할 모델 선택
model = genai.GenerativeModel('gemini-2.0-flash')

ROLE_DESCRIPTION = """
    당신은 사용자가 일기를 편리하게 쓸 수 있도록 도와주는 서비스입니다.
    모든 답변은 한글 존댓말을 사용하세요.
    사용자는 일기를 꾸준히 쓰고 싶어하는 사람입니다.
    한 번 써보고 끝이 아니라, 매일 재미를 느끼며 계속 작성할 수 있도록 동기를 부여해주세요.
"""

def generate_question_from_caption(caption: str) -> str:
    """
    이미지 캡셔닝 결과를 바탕으로 첫 번째 질문을 생성
    """
    prompt = f"""
    캡셔닝 결과: {caption}
    요청사항: {ROLE_DESCRIPTION}
    사용자가 촬영하여 업로드한 사진의 설명을 바탕으로,
    이미지에서 일기에 쓸 만한 주제를 언급하고,
    흥미롭고 답변하기 쉬운 한 가지 질문을 자연스럽게 한 줄의 문장으로 만들어주세요.
    """
    response = model.generate_content(prompt)
    return response.text.strip()

def generate_followup_question(conversation_history: list, caption: str, emotion: str = "중립") -> str:
    """
    대화 기록을 바탕으로 후속 질문 생성
    """
    history_text = "\n".join(conversation_history)

    prompt = f"""
    업로드한 사진: "{caption}"
    사용자의 감정: "{emotion}"
    지금까지의 대화 기록:
    {history_text} 

    요청사항: {ROLE_DESCRIPTION}
    위의 내용을 참고하여, 일기 작성을 좀 더 구체화하거나 흥미로운 이야기를 이끌어낼 수 있는 한 가지 후속 질문을 한글로 만들어주세요.
    주제가 반복되거나 사용자가 불편함을 느끼는 주제라고 판단될 경우 캡셔닝 결과 또는 대화 기록에서 새로운 주제를 찾으세요.
    친근하고 공감하는 어조로, 사용자의 감정을 이해하고, 감정을 조금 더 탐색할 수 있는 질문을 한 개만 만들어주세요.
    답변은 2~3문장으로 간결하게 유지하고, 예시는 1개 정도만 들어주세요.
    이전 대화 내용도 반영해주세요.
    """
    response = model.generate_content(prompt)
    return response.text.strip()

def generate_diary_draft(conversation_history: list) -> str:
    """
    대화 내용을 기반으로 일기 초안을 생성하는 함수.
    """
    full_conversation = "\n".join(conversation_history)

    prompt = f"""
    요청사항: {ROLE_DESCRIPTION}
    아래 대화 내용을 바탕으로, 사용자의 감정과 상황이 잘 드러나는 일기 초안을 작성해 주세요.
    문맥이 자연스럽고 핵심 내용이 잘 담기도록 정리하되, 
    '앞으로도 매일 일기를 쓰고 싶어지는' 동기가 될 만한 따뜻하고 희망적인 문장들을 포함해주세요.
    간결하면서도, 사용자가 자신을 돌아볼 수 있는 한두 문장과
    내일 혹은 다음 일기를 위한 작은 다짐이나 기대감이 느껴지도록 작성해 주세요.

    대화 내용:
    {full_conversation}
    """
    
    response = model.generate_content(prompt)
    return response.text.strip()


def incorporate_user_changes(original_draft, user_changes) -> str:
    """
    - original_draft: Gemini가 생성한 '초기 일기 초안'
    - user_changes: 사용자가 수정하고 싶은 내용 (여러 줄)
    이 둘을 합쳐, 최종 버전을 다시 Gemini에게 요청하여 생성.
    """
    prompt = f"""
    요청사항: {ROLE_DESCRIPTION}
    아래는 일기 초안입니다:
    ===
    {original_draft}
    ===

    사용자가 다음과 같은 수정 사항을 제시했습니다:
    ===
    {user_changes}
    ===
    
    초안의 분위기와 톤을 유지하되, 사용자의 수정이 우선 적용되어야 합니다.
    초안 처럼 '앞으로도 매일 일기를 쓰고 싶어지는' 동기가 될 만한 따뜻하고 희망적인 문장들을 포함해주세요.
    내일 혹은 다음 일기를 위한 작은 다짐이나 기대감이 느껴지도록 간결하게 작성해 주세요.
    위 수정 사항을 충실히 반영하면서도, 전체 글이 자연스럽게 이어지도록 최종 일기를 작성해 주세요.
    """
    response = model.generate_content(prompt)
    return response.text

# =================== 🎯 기능 테스트용 Main 블록 ===================
if __name__ == "__main__":
    print("\n💡 Gemini 기반 일기 작성 도우미 테스트 시작!")
    print("❗ 'exit' 입력 시 종료됩니다.\n")

    # 이미지 캡션 입력 받기
    image_caption = input("📷 업로드한 이미지 설명: ").strip()
    if not image_caption:
        image_caption = "아름다운 해변에서 석양을 바라보는 풍경"

    # 첫 번째 질문 생성
    first_question = generate_question_from_caption(image_caption)
    print(f"\n🤖 AI: {first_question}")

    # 대화 흐름 저장
    conversation_history = []
    conversation_history.append(f"AI: {first_question}")

    # 사용자와 대화 진행
    while True:
        user_answer = input("\n👤 사용자: ").strip()

        if user_answer.lower() == "exit":
            print("\n💡 대화를 종료합니다.")
            break

        conversation_history.append(f"User: {user_answer}")

        # 후속 질문 생성
        followup_question = generate_followup_question(conversation_history, image_caption)
        conversation_history.append(f"AI: {followup_question}")

        print(f"\n🤖 AI: {followup_question}")

    # 일기 초안 생성
    diary_draft = generate_diary_draft(conversation_history)
    print("\n📖 일기 초안 생성 완료!\n")
    print("=== 📝 AI가 작성한 일기 초안 ===")
    print(diary_draft)
    print("==============================")
