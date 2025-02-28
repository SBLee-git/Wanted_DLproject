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

ROLE_DESCRIPTION = "당신은 사용자가 일기를 편리하게 쓸 수 있도록 도와주는 서비스입니다."

def generate_question_from_caption(caption: str) -> str:
    """
    이미지 캡셔닝 결과를 바탕으로 첫 번째 질문을 생성
    """
    prompt = f"""
    캡셔닝 결과: {caption}
    요청사항: {ROLE_DESCRIPTION}
    사용자가 촬영하여 업로드한 이미지의 캡셔닝 결과를 바탕으로,
    이미지에서 일기에 쓸 만한 주제를 자연스럽게 한 줄로 언급하고,
    흥미롭고 답변하기 쉬운 한 가지 질문을 한글로 만들어주세요.
    """
    response = model.generate_content(prompt)
    return response.text.strip()

def generate_followup_question(conversation_history: list, caption: str) -> str:
    """
    대화 기록을 바탕으로 후속 질문 생성
    """
    history_text = "\n".join(conversation_history)

    prompt = f"""
    캡셔닝 결과: "{caption}"
    지금까지의 대화 기록:
    {history_text}

    요청사항: {ROLE_DESCRIPTION}
    위의 내용을 참고하여, 일기 작성을 좀 더 구체화하거나 흥미로운 이야기를 이끌어낼 수 있는 한 가지 후속 질문을 한글로 만들어주세요.
    주제가 반복되거나 사용자가 불편함을 느끼는 주제라고 판단될 경우 캡셔닝 결과 또는 대화 기록에서 새로운 주제를 찾으세요.
    """
    response = model.generate_content(prompt)
    return response.text.strip()

def generate_diary_draft(conversation_history: list) -> str:
    """
    대화 내용을 기반으로 일기 초안을 생성하는 함수.
    """
    full_conversation = "\n".join(conversation_history)

    prompt = f"""
    다음은 사용자와 서비스(당신) 간의 대화 내용입니다:
    {full_conversation}

    역할: {ROLE_DESCRIPTION}
    요청사항: 위 대화 내용을 바탕으로, 사용자 입장에서 쓸 수 있는 일기 초안을 한글로 작성해주세요.
    문맥과 감정을 담되, 이모지를 사용하지 않고, 간결하고 자연스러운 문장으로 요약하여 작성해주시기 바랍니다.
    """
    response = model.generate_content(prompt)
    return response.text.strip()
