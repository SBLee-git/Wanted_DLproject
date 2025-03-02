from datetime import datetime
import requests
from PIL import Image
import torch
from transformers import LlavaForConditionalGeneration, BitsAndBytesConfig, LlavaProcessor


class LlavaImageCaptioning:
    """
    LLaVA 기반 이미지 캡셔닝 클래스.
    
    1. 모델을 로드 및 설정
    2. 이미지 입력 (URL 또는 파일)
    3. 이미지에 대한 캡션 생성
    """

    def __init__(self, model_path="./models/llava-1.5-7b-hf"):
        """
        클래스 초기화 및 모델 로드.

        Args:
            model_path (str): 로컬에 저장된 LLaVA 모델 경로
        """
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model_path = model_path
        self.processor, self.model = self.load_model()

    def load_model(self):
        """
        LLaVA 모델 및 프로세서를 로드합니다.

        Returns:
            processor (LlavaProcessor): 텍스트 & 이미지 전처리를 위한 프로세서
            model (LlavaForConditionalGeneration): LLaVA 모델 객체
        """
        print("모델을 로드 중...")
        try:
            # BitsAndBytes 4-bit 양자화 설정
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4"
            )
        except:  # TODO
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=False  # CPU에서는 4비트 양자화 지원 X
            )
        # 프로세서 및 모델 로드
        processor = LlavaProcessor.from_pretrained(self.model_path, use_fast=False)
        model = LlavaForConditionalGeneration.from_pretrained(
            self.model_path,
            torch_dtype=torch.float16,
            quantization_config=bnb_config,
            low_cpu_mem_usage=True
        ).to(self.device)

        print("모델 로드 완료!")
        return processor, model

    def load_image_from_url(self, img_url):
        """
        URL에서 이미지를 로드합니다.

        Args:
            img_url (str): 이미지의 URL

        Returns:
            PIL.Image: 로드된 이미지 객체
        """
        try:
            image = Image.open(requests.get(img_url, stream=True).raw).convert("RGB")
            print("✅ 이미지 로드 성공 (URL)")
            return image
        except Exception as e:
            print("❌ 이미지 로드 실패:", str(e))
            return None

    def load_image_from_file(self, file_path):
        """
        업로드된 파일에서 이미지를 로드합니다.

        Args:
            file_path (str): 로컬 파일 경로

        Returns:
            PIL.Image: 로드된 이미지 객체
        """
        try:
            image = Image.open(file_path).convert("RGB")
            print("✅ 이미지 로드 성공 (파일)")
            return image
        except Exception as e:
            print("❌ 이미지 로드 실패:", str(e))
            return None

    def generate_caption(self, image, prompt_text="Describe the image in detail."):
        """
        LLaVA 모델을 사용하여 이미지 캡션을 생성합니다.

        Args:
            image (PIL.Image): 캡션을 생성할 이미지 객체
            prompt_text (str): 이미지 설명을 요청하는 프롬프트

        Returns:
            str: 생성된 이미지 캡션
            timedelta: 실행 시간
        """
        if image is None:
            print("❌ 이미지가 제공되지 않았습니다.")
            return None, None

        # 실행 시간 측정 시작
        start_time = datetime.now()

        # 대화 프롬프트 설정
        conversation = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt_text},
                    {"type": "image"},
                ],
            },
        ]

        # 프롬프트 변환
        prompt = self.processor.apply_chat_template(conversation, add_generation_prompt=False)

        # 모델 입력 처리
        inputs = self.processor(images=image, text=prompt, return_tensors="pt").to(self.device, torch.float16)

        # 모델 추론
        with torch.no_grad():
            output_ids = self.model.generate(**inputs, max_new_tokens=200, do_sample=False)

        # 결과 디코딩
        caption = self.processor.decode(output_ids[0], skip_special_tokens=True)

        # 실행 시간 계산
        execution_time = datetime.now() - start_time

        return caption, execution_time


# =================== 사용 예시 ===================

if __name__ == "__main__":
    captioner = LlavaImageCaptioning()  # 모델 로드

    # 이미지 URL 입력받기
    img_url = input("Enter the image URL: ").strip()
    if not img_url:
        # img_url = "https://storage.googleapis.com/sfr-vision-language-research/BLIP/demo.jpg"
        img_url = "https://search.pstatic.net/common/?src=http%3A%2F%2Fcafefiles.naver.net%2FMjAxOTA5MTNfMzIg%2FMDAxNTY4MzY1NjY5ODg5.BQj_C13jNjHbjJA06-8TqRKAOzWBIzmd-TI6k4uKhvIg.Zk4o2ehGsRDLLNy6LRGly4_M1zFXjwT9bX9_jkigLTkg.JPEG%2FexternalFile.jpg"

    # URL로 이미지 로드
    image = captioner.load_image_from_url(img_url)

    # 캡션 생성
    caption, exec_time = captioner.generate_caption(image)

    # 결과 출력
    print("Execution Time:", exec_time)
    print("\nGenerated Caption:\n", caption.split('\n'))
