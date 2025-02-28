import torch
from transformers import BertForSequenceClassification, AutoTokenizer
import re
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

class EmotionClassifier:
    def __init__(self, model_path="monologg/kobert", num_labels=7, device=None):
        """
        감정 분류 모델 초기화 및 로드
        """
        self.device = device if device else ("cuda" if torch.cuda.is_available() else "cpu")
        self.model = BertForSequenceClassification.from_pretrained(model_path, num_labels=num_labels)
        self.tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)  # trust_remote_code = 모델 다운로드에 대한 검증 절차 생략
        self.load_params("./models/kobert_emotion.pth")
        self.model.to(self.device)

        # 감정 매핑 (라벨 -> 감정명)
        self.label_to_emotion = {
            0: "중립",
            1: "놀람",
            2: "분노",
            3: "슬픔",
            4: "행복",
            5: "혐오",
            6: "공포"
        }

    def load_params(self, model_file):
        """학습된 감정 분류 모델 불러오기"""
        self.model.load_state_dict(torch.load(model_file, map_location=self.device))

    def preprocess_text(self, text):
        """텍스트 전처리"""
        return re.sub("[^0-9a-zA-Z가-힣\s+]", "", text)

    def predict_emotion(self, text):
        """감정 분류 및 예측"""
        cleaned_text = self.preprocess_text(text)
        encoded_input = self.tokenizer(cleaned_text, return_tensors="pt", truncation=True, padding="max_length", max_length=128)
        encoded_input = {key: val.to(self.device) for key, val in encoded_input.items()}
        
        # 예측 수행
        self.model.eval()
        with torch.no_grad():
            outputs = self.model(**encoded_input)
            predicted_label = outputs.logits.argmax(dim=1).item()
        
        # 감정 매핑 반환
        predicted_emotion = self.label_to_emotion[predicted_label]
        return predicted_emotion
    
    

if __name__ == "__main__":
    emotion_classifier = EmotionClassifier()  # 감정 분석기 객체 생성

    print("\n💡 감정 분석 테스트")
    print("종료하려면 'exit' 입력\n")

    while True:
        user_text = input("👤 입력 문장: ").strip()

        if user_text.lower() == "exit":
            print("\n👋 테스트 종료!")
            break

        emotion = emotion_classifier.predict_emotion(user_text)
        print(f"🤖 감정 분석 결과: {emotion}\n")
    