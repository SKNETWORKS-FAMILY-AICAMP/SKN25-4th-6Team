#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
105개 전체 카드 PDF -> JSON 배치 추출 및 자동 재색인

용도: 초기 전체 데이터셋 생성 또는 주기적 전체 갱신
"""

import argparse
import subprocess as _sp
import sys
from pathlib import Path
from typing import List


def is_image_pdf(pdf_path: Path, threshold: int = 100) -> bool:
    """pdftotext 추출 결과가 threshold자 미만이면 이미지 PDF로 판단."""
    result = _sp.run(
        ["pdftotext", "-layout", str(pdf_path), "-"],
        capture_output=True, text=True, check=False,
    )
    return len((result.stdout or "").strip()) < threshold


def run_card_analyzer(pdf_path: Path, output_dir: Path, timeout: int = 180) -> bool:
    """card_analyzer.py를 호출해 PDF -> JSON 변환"""
    script_path = Path(__file__).resolve().parent / "card_analyzer.py"
    output_name = pdf_path.stem + ".json"
    output_path = output_dir / output_name

    result = _sp.run(
        [sys.executable, str(script_path), "--pdf", str(pdf_path), "--output", str(output_path)],
        capture_output=True,
        timeout=timeout,
    )
    return result.returncode == 0


def find_all_pdfs(root_dir: Path) -> List[Path]:
    """raw 디렉토리 하위 모든 PDF 찾기"""
    pdfs = list(root_dir.glob("**/*.pdf"))
    return sorted([p for p in pdfs if p.is_file()])


def main() -> None:
    parser = argparse.ArgumentParser(description="105개 전체 카드 PDF 배치 추출 + 재색인")
    parser.add_argument("--raw-dir", default="raw", help="원본 PDF 디렉토리")
    parser.add_argument("--data-dir", default="data/cards", help="출력 JSON 디렉토리")
    parser.add_argument("--skip-existing", action="store_true", help="이미 있는 JSON은 스킵")
    parser.add_argument("--force", action="store_true", help="이미 있는 JSON도 덮어쓰기")
    parser.add_argument("--image-only", action="store_true", help="이미지 PDF(텍스트 추출 불가)만 처리")
    parser.add_argument("--rebuild-index", action="store_true", help="완료 후 RAG 인덱스 재생성")
    parser.add_argument("--limit", type=int, default=0, help="최대 처리 개수 (0=무제한)")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent
    raw_dir = (project_root / args.raw_dir).resolve()
    data_dir = (project_root / args.data_dir).resolve()
    data_dir.mkdir(parents=True, exist_ok=True)

    pdfs = find_all_pdfs(raw_dir)
    if not pdfs:
        print(f"[WARN] PDF 없음: {raw_dir}")
        return

    if args.skip_existing:
        existing = {f.stem for f in data_dir.glob("*.json")}
        pdfs = [p for p in pdfs if p.stem not in existing]

    if args.image_only:
        print("[INFO] 이미지 PDF 스캔 중...")
        image_pdfs = []
        for p in pdfs:
            if is_image_pdf(p):
                image_pdfs.append(p)
                print(f"  이미지 PDF: {p.name}")
        pdfs = image_pdfs
        print(f"[INFO] 이미지 PDF {len(pdfs)}개 발견")

    if args.limit > 0:
        pdfs = pdfs[: args.limit]

    total_all = len(find_all_pdfs(raw_dir))
    print(f"[INFO] 처리할 PDF: {len(pdfs)}/{total_all}")

    success = 0
    fail = 0
    for idx, pdf_path in enumerate(pdfs, start=1):
        output_name = pdf_path.stem + ".json"
        output_path = data_dir / output_name

        if output_path.exists() and not args.force:
            print(f"[{idx}/{len(pdfs)}] SKIP: {pdf_path.name}")
            success += 1
            continue

        print(f"[{idx}/{len(pdfs)}] 처리 중: {pdf_path.name}")
        # 이미지 PDF는 Vision API 호출로 시간이 더 걸림 → timeout 늘림
        timeout = 600 if args.image_only else 180
        try:
            if run_card_analyzer(pdf_path, data_dir, timeout=timeout):
                success += 1
                print(f"       OK: {output_name}")
            else:
                fail += 1
                print(f"       FAIL: {pdf_path.name} (analyzer 실패)")
        except Exception as e:
            fail += 1
            print(f"       ERROR: {pdf_path.name} ({e})")

    print("=" * 70)
    print(f"[SUMMARY] 성공={success}, 실패={fail}, 총={len(pdfs)}")
    print("=" * 70)

    if args.rebuild_index:
        print("[INFO] RAG 인덱스 재생성 중...")
        rebuild_script = Path(__file__).resolve().parent / "rebuild_rag_index.sh"
        if rebuild_script.exists():
            import subprocess

            result = subprocess.run([str(rebuild_script)], capture_output=True, timeout=600)
            if result.returncode == 0:
                print("[OK] RAG 인덱스 재생성 완료")
            else:
                print(f"[WARN] RAG 인덱스 재생성 실패: {result.stderr.decode('utf-8', errors='replace')}")
        else:
            print(f"[WARN] 재색인 스크립트 없음: {rebuild_script}")


if __name__ == "__main__":
    main()
