# CLAUDE.md

**언어**: 모든 응답은 한국어로 작성한다. 코드·명령어·파일명은 그대로 유지.

건물 패치 평가 대시보드(fo_building_eval) → demo-fiftyone-dashboard 템플릿 기반 이관 프로젝트.

## 라우팅


| 작업              | 스킬                  |
| --------------- | ------------------- |
| 이관 시작·재실행·부분 수정 | `migrate-dashboard` |
| 속성 1개 추가·교체     | `port-attribute`    |
| 커밋              | `commit-convention` |


단순 질문은 직접 응답 가능.

## 핵심 불변식

1. `**config.py`가 단일 진실 소스.** `PANEL_COLUMN_META` / `ATTRIBUTE_GROUPS` / `DATASETS` / `_EXPERIMENT_LABELS` 에만 등록 → 파이프라인·패널 자동 전파. 다른 파일 하드코딩 금지.
2. **건물 속성은 랜덤 `generate` 금지.** 기하20/방사4 = 현재 24종이 실제 compute 함수에 연결됨. VLM 3종·기하 2종(bd_type_area_ratio/bd_type_count)은 미구현 백로그 — 추가 시 `port-attribute` 스킬 사용.
3. **데이터 준비(TIF/SHP → FiftyOne 적재)는 이 프로젝트 외부.** 하네스는 데이터가 이미 FiftyOne에 있다고 가정한다.

## 비자명 주의 사항

- `plugins/fiftyone.yml` **ASCII 전용.** 한글·em-dash·원형숫자 포함 시 FiftyOne이 플러그인을 무음으로 무시.
- `config.activate_dataset()` 는 모듈 전역(DATA_DIR 등)을 변경한다. 데이터셋별 작업은 반드시 `main.py`의 `_build_all_datasets` 루프 안에서 실행.
- **속성 vs 메트릭 구분**: "예측 마스크를 바꾸면 이 값도 바뀌는가?" → yes=metric, no=attribute.
- 일상 명령은 `make run` 하나면 충분 (config.py 변경 자동 감지 → attrs/stats 재생성).

## 변경 이력


| 날짜         | 변경 내용         | 대상  | 사유  |
| ---------- | ------------- | --- | --- |
| 2026-06-23 | 이관용 하네스 초기 구성 | 전체  | -   |


