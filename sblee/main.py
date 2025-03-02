from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import torch
from transformers import BertForSequenceClassification, AutoTokenizer, AutoModel
import re
from sklearn.metrics.pairwise import cosine_similarity
import pandas as pd
import google.generativeai as genai
import numpy as np 
import sys
import os
sys.path.append(os.path.abspath(".."))  # 현재 디렉터리의 상위 경로 추가

from config.api_keys import gemini_key

# -------------------------------
#  첫 번째 감정 분류 (KoBERT)
# -------------------------------
class EmotionClassifier:
    def __init__(self, model_path="monologg/kobert", num_labels=7, device=None):
        self.device = device if device else ("cuda" if torch.cuda.is_available() else "cpu")
        self.model = BertForSequenceClassification.from_pretrained(model_path, num_labels=num_labels)
        self.tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
        self.model.to(self.device)

        self.label_to_emotion = {
            0: "중립",
            1: "놀람",
            2: "분노",
            3: "슬픔",
            4: "행복",
            5: "혐오",
            6: "공포"
        }

    def load_model(self, model_file):
        self.model.load_state_dict(torch.load(model_file, map_location=self.device))

    def preprocess_text(self, text):
        return re.sub("[^0-9a-zA-Z가-힣\s+]", "", text)

    def predict_emotion(self, text):
        cleaned_text = self.preprocess_text(text)
        encoded_input = self.tokenizer(
            cleaned_text,
            return_tensors="pt",
            truncation=True,
            padding="max_length",
            max_length=128
        )
        encoded_input = {key: val.to(self.device) for key, val in encoded_input.items()}

        self.model.eval()
        with torch.no_grad():
            outputs = self.model(**encoded_input)
            predicted_label = outputs.logits.argmax(dim=1).item()

        return self.label_to_emotion[predicted_label]

# -----------------------------
#  E5 임베딩 클래스
# -----------------------------
class E5Embedder:
    def __init__(self):
        self.tokenizer = AutoTokenizer.from_pretrained("intfloat/e5-large")
        self.model = AutoModel.from_pretrained("intfloat/e5-large")

    def get_embedding(self, text):
        inputs = self.tokenizer(text, return_tensors="pt", truncation=True)
        with torch.no_grad():
            outputs = self.model(**inputs)
        
        embedding = outputs.last_hidden_state.mean(dim=1).detach()
        return embedding

# -----------------------------
#  노래 추천(코사인 유사도)
# -----------------------------
class SongRecommender:
    def __init__(self, df):
        self.df = df

    def recommend_song(self, diary_embedding, emotion):
        filtered_df = self.df[self.df['emotion'] == emotion]

        similarities = []
        if isinstance(diary_embedding, torch.Tensor):
            diary_emb_np = diary_embedding.numpy()
        else:
            diary_emb_np = diary_embedding

        for _, row in filtered_df.iterrows():
            song_emb = row['embedding']
            if isinstance(song_emb, torch.Tensor):
                song_emb = song_emb.numpy()

            sim = cosine_similarity(diary_emb_np, song_emb)
            similarities.append((
                row['title'],
                row['artist'],
                row['cleaned_lyrics'],
                sim[0][0]
            ))

        if similarities:
            best_match = sorted(similarities, key=lambda x: x[3], reverse=True)[0]
            return best_match
        else:
            return None

# FastAPI 앱 초기화
app = FastAPI()

# 모델 및 추천기 초기화
emotion_classifier = EmotionClassifier()
emotion_classifier.load_model("./new_data_test.pth")  # 실제 모델 파일 경로로 교체해주세요
e5_embedder = E5Embedder()

# 노래 데이터 로드 (실제 데이터로 교체해야 합니다)
df = pd.read_pickle("./trot_embeddings_emotion.pkl")
song_recommender = SongRecommender(df)

# Gemini 설정
genai.configure(api_key=gemini_key)  # 실제 API 키로 교체해주세요
gemini_model = genai.GenerativeModel('gemini-2.0-flash')

chat_history = []

def ask_gemini(user_response, emotion, max_history_length=5):
    global chat_history

    conversation_history = "\n".join(chat_history)
    
    full_prompt = (
        f"{conversation_history}"
        f"\nUser (감정: {emotion}): {user_response}\n\n"
        "사용자는 일기를 꾸준히 쓰고 싶어하는 사람입니다. "
        "한 번 써보고 끝이 아니라, 매일 재미를 느끼며 계속 작성할 수 있도록 동기를 부여해주세요. "
        "친근하고 공감하는 어조로, 사용자의 감정을 이해하고, 감정을 조금 더 탐색할 수 있는 질문을 한 개만 만들어주세요. "
        "답변은 2~3문장으로 간결하게 유지하고, 예시는 1개 정도만 들어주세요. "
        "이전 대화 내용도 반영해주세요."
    )

    response = gemini_model.generate_content(full_prompt)

    chat_history.append(f"User (감정: {emotion}): {user_response}")
    chat_history.append(f"Gemini: {response.text}")

    if len(chat_history) > max_history_length * 2:
        chat_history = chat_history[-(max_history_length * 2):]

    return response.text

def generate_diary_draft(chat_history):
    full_conversation = "\n".join(chat_history)
    
    prompt = f"""
    아래 대화 내용을 바탕으로, 사용자의 감정과 상황이 잘 드러나는 일기 초안을 작성해 주세요.
    문맥이 자연스럽고 핵심 내용이 잘 담기도록 정리하되, 
    '앞으로도 매일 일기를 쓰고 싶어지는' 동기가 될 만한 따뜻하고 희망적인 문장들을 포함해주세요.
    간결하면서도, 사용자가 자신을 돌아볼 수 있는 한두 문장과
    내일 혹은 다음 일기를 위한 작은 다짐이나 기대감이 느껴지도록 작성해 주세요.

    대화 내용:
    "{full_conversation}"
    """

    response = gemini_model.generate_content(prompt)
    return response.text

def suggest_activities_and_products(diary_text, emotion):
    prompt = f"""
    당신은 일기를 작성하는 사람을 돕는 조력자입니다.
    아래는 사용자의 일기 초안과 감정 상태입니다.
    
    일기: "{diary_text}"
    감정: {emotion}
    
    이 사용자에게 적합한 기분전환 활동을 두세 가지 정도 제안하고,
    도움이 될 만한 상품이나 서비스를 하나 이상 추천해주세요.
    답변은 간결하게, 핵심만 정리해 주세요.사용자 입장에서 어렵지 않게 시도해볼 수 있는 활동을 알려주세요.
    """
    response = gemini_model.generate_content(prompt)
    return response.text

class DiaryEntry(BaseModel):
    text: str

@app.post("/process_diary")
async def process_diary(entry: DiaryEntry):
    global chat_history
    
    # 감정 분류
    emotion = emotion_classifier.predict_emotion(entry.text)
    
    # E5 임베딩
    diary_embedding = e5_embedder.get_embedding(entry.text)
    
    # 노래 추천
    recommended_song = song_recommender.recommend_song(diary_embedding, emotion)
    
    # Gemini 대화
    gemini_response = ask_gemini(entry.text, emotion)
    
    # 일기 초안 생성
    chat_history.append(f"User: {entry.text}")
    chat_history.append(f"Gemini: {gemini_response}")
    diary_draft = generate_diary_draft(chat_history)
    
    # 활동 및 상품 추천
    suggestions = suggest_activities_and_products(diary_draft, emotion)
    
    return {
        "emotion": emotion,
        "recommended_song": recommended_song,
        "gemini_response": gemini_response,
        "diary_draft": diary_draft,
        "suggestions": suggestions
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)