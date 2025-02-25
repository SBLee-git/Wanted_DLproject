from datetime import datetime
import requests
from PIL import Image
import torch
from transformers import AutoProcessor, LlavaForConditionalGeneration, BitsAndBytesConfig, LlavaProcessor


def generate_image_caption(img_url, model_id="llava-hf/llava-1.5-7b-hf", prompt_text="Describe the image in detail."):
    """
    LLaVA 모델을 사용하여 이미지 캡션을 생성하는 함수.
    
    Args:
        img_url (str): 분석할 이미지의 URL
        model_id (str): 사용할 LLaVA 모델 ID (기본값: "llava-hf/llava-1.5-7b-hf")
        prompt_text (str): 이미지에 대한 설명을 요청하는 프롬프트 (기본값: 상세 설명 요청)
    
    Returns:
        str: 생성된 이미지 캡션
        timedelta: 실행 시간
    """

    device = "cuda" if torch.cuda.is_available() else "cpu"
    
    # huggingface-cli download llava-hf/llava-1.5-7b-hf --local-dir ./models/llava-1.5-7b-hf --local-dir-use-symlinks False
    local_model_path = "./models/llava-1.5-7b-hf"
    
    # BitsAndBytes 4-bit 양자화 설정
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4"
    )

    # 모델 및 프로세서 로드
    # processor = LlavaProcessor.from_pretrained(model_id, use_fast=True)
    processor = LlavaProcessor.from_pretrained(local_model_path, use_fast=True)
    model = LlavaForConditionalGeneration.from_pretrained(
        # model_id,
        local_model_path,
        torch_dtype=torch.float16,
        quantization_config=bnb_config,
        low_cpu_mem_usage=True
    ).to(device)

    # 이미지 로드 및 RGB 변환
    raw_image = Image.open(requests.get(img_url, stream=True).raw).convert("RGB")

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

    # 실행 시간 측정 시작
    start_time = datetime.now()

    # 프롬프트 변환
    prompt = processor.apply_chat_template(conversation, add_generation_prompt=False)

    # 모델 입력 처리
    inputs = processor(images=raw_image, text=prompt, return_tensors="pt").to(device, torch.float16)

    # 모델 추론
    with torch.no_grad():
        output_ids = model.generate(**inputs, max_new_tokens=200, do_sample=False)

    # 결과 디코딩
    caption = processor.decode(output_ids[0][2:], skip_special_tokens=True)
    print('test1', processor.decode(output_ids[0][6:], skip_special_tokens=True))

    # 실행 시간 계산
    execution_time = datetime.now() - start_time

    return caption, execution_time

# 사용 예제
if __name__ == "__main__":
    img_url = input("Enter the image URL: ").strip()
    if not img_url:
        img_url = "https://storage.googleapis.com/sfr-vision-language-research/BLIP/demo.jpg"
    caption, exec_time = generate_image_caption(img_url)
    
    print("Execution Time:", exec_time)
    print("\nGenerated Caption:\n", caption)



