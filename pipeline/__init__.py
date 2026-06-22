"""
pipeline — 매 실행마다 돌아가는 분석 단계 모음 (위계: 분석)

각 모듈의 역할:
  dataset_builder  : manifest(마스크 경로) + tags.json(속성) → fo.Dataset 구축
  evaluation       : evaluate_segmentations 실행 + per-class report 출력
  visualization    : confusion matrix PNG 저장 + plotly 인터랙티브 표시
  app              : fo.launch_app 실행 + App 사용법 안내

사용 위계:
  tools/*      — 1회성 데이터 준비 (build_manifest, generate_attrs)
  pipeline/*   — 매 실행 분석 (build → evaluate → visualize → app)
  main.py      — 얇은 오케스트레이터 (위 단계를 순서대로 호출)
"""
