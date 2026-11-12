"""4단계 이미지 생성: 프롬프트와 제품 사진을 FLUX.2 [klein] 4B에 넣어 이미지를 만듭니다.

필요 사양
- NVIDIA GPU, VRAM 약 13GB 이상 (모델 카드 기준: RTX 3090 / 4070 이상)
- 첫 실행 때 모델 약 16GB를 내려받습니다 (Hugging Face 캐시에 저장).

실행: python generate_image.py
결과: output/ 폴더에 이미지(.png)와 사용한 프롬프트·설정(.json)을 같은 이름으로 저장합니다.
"""
import json
import time
from datetime import datetime

import torch
from diffusers import Flux2KleinPipeline
from PIL import Image

from build_prompt import BASE_DIR, build_prompt, image_paths, load_retrieval

MODEL_ID = "black-forest-labs/FLUX.2-klein-4B"
NUM_INFERENCE_STEPS = 4  # 모델 카드 예시 값
GUIDANCE_SCALE = 1.0  # 모델 카드 예시 값
SEED = 0  # 같은 시드면 같은 결과가 나옵니다.
CPU_OFFLOAD = True  # 쓰지 않는 부분을 CPU 메모리로 내려 VRAM을 아낍니다. VRAM이 넉넉하면 False가 더 빠릅니다.
FILL_COLOR = (255, 255, 255)  # 투명 배경을 채울 색
OUTPUT_DIR = BASE_DIR / "output"


def load_reference(path):
    """제품 사진을 RGB로 불러옵니다.

    투명 배경 PNG를 그냥 RGB로 바꾸면 투명한 부분이 검정이 되므로 FILL_COLOR로 채웁니다.
    """
    image = Image.open(path)
    if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
        image = image.convert("RGBA")
        filled = Image.new("RGB", image.size, FILL_COLOR)
        filled.paste(image, mask=image.getchannel("A"))
        return filled
    return image.convert("RGB")


def load_pipeline():
    pipe = Flux2KleinPipeline.from_pretrained(MODEL_ID, torch_dtype=torch.bfloat16)
    if CPU_OFFLOAD:
        pipe.enable_model_cpu_offload()
    else:
        pipe.to("cuda")
    return pipe


def main():
    if not torch.cuda.is_available():
        raise SystemExit("CUDA를 쓸 수 있는 NVIDIA GPU를 찾지 못했습니다. CUDA용 torch가 설치됐는지 확인하세요.")

    retrieval = load_retrieval()
    prompt = build_prompt(retrieval)
    reference_paths = image_paths(retrieval)
    references = [load_reference(path) for path in reference_paths]
    print(prompt, end="\n\n")

    print(f"모델 불러오는 중: {MODEL_ID}")
    pipe = load_pipeline()

    # 출력 크기(height, width)는 지정하지 않습니다. 파이프라인이 첫 번째 참고 사진의 비율을 따릅니다.
    started = time.time()
    image = pipe(
        image=references,
        prompt=prompt,
        num_inference_steps=NUM_INFERENCE_STEPS,
        guidance_scale=GUIDANCE_SCALE,
        generator=torch.Generator(device="cuda").manual_seed(SEED),
    ).images[0]
    seconds = round(time.time() - started, 1)

    OUTPUT_DIR.mkdir(exist_ok=True)
    stem = f"keypoint_{datetime.now():%Y%m%d_%H%M%S}"
    image_path = OUTPUT_DIR / f"{stem}.png"
    image.save(image_path)
    record = {
        "model": MODEL_ID,
        "prompt": prompt,
        "reference_images": [str(path.relative_to(BASE_DIR)) for path in reference_paths],
        "num_inference_steps": NUM_INFERENCE_STEPS,
        "guidance_scale": GUIDANCE_SCALE,
        "seed": SEED,
        "fill_color": FILL_COLOR,
        "output_size": image.size,
        "seconds": seconds,
    }
    (OUTPUT_DIR / f"{stem}.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"완료 ({seconds}초): {image_path}  크기 {image.size[0]}x{image.size[1]}")


if __name__ == "__main__":
    main()
