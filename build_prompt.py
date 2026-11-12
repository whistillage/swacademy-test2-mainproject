"""3단계 프롬프트 구성: 그래프 검색 결과(JSON)로 이미지 생성 프롬프트를 만듭니다.

프롬프트에는 그래프에서 가져온 값만 넣습니다. 고정 문구는 목적 문장 하나뿐입니다.
무거운 라이브러리가 필요 없어서 GPU가 없는 PC에서도 실행할 수 있습니다.

실행: python build_prompt.py
      만들어진 프롬프트와, 함께 넣을 제품 사진의 경로를 출력합니다.
"""
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
RETRIEVAL_FILE = BASE_DIR / "data" / "keypoint_retrieval.json"  # 2단계 그래프 검색 결과(가정)
STORAGE_ROOT = BASE_DIR / "assets"  # 파일 저장소 역할. 그래프의 uri는 이 폴더 기준 상대 경로입니다.

PURPOSE = "온라인 쇼핑몰 상품 상세 페이지의 '키포인트' 섹션 이미지 1장을 만든다."


def load_retrieval(path=RETRIEVAL_FILE):
    """그래프 검색 결과 JSON을 읽습니다."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_prompt(result):
    """검색 결과의 값을 정해진 칸에 채워 프롬프트 문자열을 만듭니다."""
    evidence = result["evidence"]
    colors = result["design"]["colors"]
    typography = result["design"]["typography"]
    lines = [
        "[목적]",
        PURPOSE,
        "",
        "[문구]",
        f'"{result["claim"]}"',
        "",
        "[근거]",
        f"- 유형: {evidence['type']}",
        f"- 기간: {evidence['period']['start']} ~ {evidence['period']['end']}",
        f"- 대상 제품: {', '.join(evidence['covers'])}",
        "",
        "[제품 이미지]",
        *(f"- 첨부 이미지 {number}: {image['view']}, 배경 {image['background']}"
          for number, image in enumerate(result["images"], start=1)),
        "",
        "[브랜드 컬러]",
        f"- 메인: {colors['main']}",
        f"- 보조: {colors['sub']}",
        "",
        "[폰트]",
        f"- 글꼴: {typography['font_family']}",
        f"- 글자 크기: 제목 {typography['title_px']}px, 부제목 {typography['subtitle_px']}px, "
        f"본문 {typography['body_px']}px",
    ]
    return "\n".join(lines)


def image_paths(result, storage_root=STORAGE_ROOT):
    """검색 결과의 uri를 실제 파일 경로로 바꿉니다.

    순서는 검색 결과 그대로이며, 프롬프트의 '첨부 이미지 N' 번호와 같아야 합니다.
    """
    root = Path(storage_root).resolve()
    paths = []
    for image in result["images"]:
        path = (root / image["uri"]).resolve()
        if not path.is_relative_to(root):
            raise ValueError(f"저장소 밖을 가리키는 uri입니다: {image['uri']}")
        if not path.exists():
            raise FileNotFoundError(f"제품 사진이 없습니다: {path}")
        paths.append(path)
    return paths


if __name__ == "__main__":
    retrieval = load_retrieval()
    print(build_prompt(retrieval))
    print()
    for number, path in enumerate(image_paths(retrieval), start=1):
        print(f"첨부 이미지 {number}: {path}")
