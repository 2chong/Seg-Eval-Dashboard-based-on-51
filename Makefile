PYTHON   = python
DS      ?= jungrang_2022

# 모든 데이터셋 목록 — 새 데이터셋 추가 시 여기와 config.DATASETS 만 편집.
DATASETS = seocho_2022 gangseo_2022 junggu_2022 \
           jungrang_2022 mapo_2022 songpa_2022 \
           suseo_2022 yangcheon_2022 youngdeungpo_2022

# =============================================================================
# 수동 sync (통상 make run 의 auto-sync 로 불필요 — 강제 재생성이 필요할 때만)
#   make sync                        <- 기본 데이터셋만
#   make sync DS=coco-val-voc-50b   <- 특정 데이터셋
#   make sync-all                   <- 모든 데이터셋
# =============================================================================
.PHONY: sync
sync:
	$(PYTHON) tools/generate_attrs.py --dataset $(DS)
	$(PYTHON) tools/precompute_panel_stats.py --dataset $(DS)

.PHONY: sync-all
sync-all:
	$(foreach ds,$(DATASETS),\
		$(PYTHON) tools/generate_attrs.py --dataset $(ds) && \
		$(PYTHON) tools/precompute_panel_stats.py --dataset $(ds) && ) true

# =============================================================================
# App 실행 (주 명령)
#   make run                       <- 기본 데이터셋 (config.py 변경 시 자동 sync 포함)
#   make run DS=coco-val-voc-50b   <- 특정 데이터셋
# =============================================================================
.PHONY: run
run:
	$(PYTHON) main.py --dataset $(DS)

# =============================================================================
# 최초 파이프라인 (inference 미실행 시, 또는 새 데이터셋 추가 시)
#   make pipeline                       <- DS 기본값
#   make pipeline DS=coco-val-voc-50b   <- 특정 데이터셋
# 이후에는 make run 만으로 충분합니다.
# =============================================================================
.PHONY: pipeline
pipeline: manifest attrs stats

# 1단계: 패치 PNG + 마스크 + manifest 생성 (최초 1회)
.PHONY: manifest
manifest:
	$(PYTHON) oneoff/build_manifest.py --dataset $(DS)

.PHONY: manifest-all
manifest-all:
	$(PYTHON) oneoff/build_manifest.py --dataset seocho_2022
	$(PYTHON) oneoff/build_manifest.py --dataset gangseo_2022
	$(PYTHON) oneoff/build_manifest.py --dataset junggu_2022
	$(PYTHON) oneoff/build_manifest.py --dataset jungrang_2022
	$(PYTHON) oneoff/build_manifest.py --dataset mapo_2022
	$(PYTHON) oneoff/build_manifest.py --dataset songpa_2022
	$(PYTHON) oneoff/build_manifest.py --dataset suseo_2022
	$(PYTHON) oneoff/build_manifest.py --dataset yangcheon_2022
	$(PYTHON) oneoff/build_manifest.py --dataset youngdeungpo_2022

# 기존 PNG 캐시(이미지·마스크)를 버리고 강제 재생성
.PHONY: manifest-force
manifest-force:
	$(PYTHON) oneoff/build_manifest.py --dataset $(DS) --force

# 2단계: 샘플 속성 생성 (manifest 변경 시 재실행)
.PHONY: attrs
attrs:
	$(PYTHON) tools/generate_attrs.py --dataset $(DS)

.PHONY: attrs-all
attrs-all:
	$(PYTHON) tools/generate_attrs.py --dataset seocho_2022
	$(PYTHON) tools/generate_attrs.py --dataset gangseo_2022
	$(PYTHON) tools/generate_attrs.py --dataset junggu_2022
	$(PYTHON) tools/generate_attrs.py --dataset jungrang_2022
	$(PYTHON) tools/generate_attrs.py --dataset mapo_2022
	$(PYTHON) tools/generate_attrs.py --dataset songpa_2022
	$(PYTHON) tools/generate_attrs.py --dataset suseo_2022
	$(PYTHON) tools/generate_attrs.py --dataset yangcheon_2022
	$(PYTHON) tools/generate_attrs.py --dataset youngdeungpo_2022

# 3단계: 패널 통계 집계 (attrs 변경 시 재실행)
.PHONY: stats
stats:
	$(PYTHON) tools/precompute_panel_stats.py --dataset $(DS)

.PHONY: stats-all
stats-all:
	-$(PYTHON) tools/precompute_panel_stats.py --dataset seocho_2022
	-$(PYTHON) tools/precompute_panel_stats.py --dataset gangseo_2022
	-$(PYTHON) tools/precompute_panel_stats.py --dataset junggu_2022
	-$(PYTHON) tools/precompute_panel_stats.py --dataset jungrang_2022
	-$(PYTHON) tools/precompute_panel_stats.py --dataset mapo_2022
	-$(PYTHON) tools/precompute_panel_stats.py --dataset songpa_2022
	-$(PYTHON) tools/precompute_panel_stats.py --dataset suseo_2022
	-$(PYTHON) tools/precompute_panel_stats.py --dataset yangcheon_2022
	-$(PYTHON) tools/precompute_panel_stats.py --dataset youngdeungpo_2022

# =============================================================================
# config.py 수정 후 업데이트 타겟
#
# 새 속성 추가 (PANEL_COLUMN_META 에 attribute + generate 등록 후):
#   make regen-attr              <- DS 기본값
#   make regen-attr DS=coco-val-voc-50b
#   make regen-attr-all          <- 모든 데이터셋 (DATASETS 변수 기반)
#
# 새 평가지표 추가 (config 에 metric + compute 등록 + precompute 코드 변경 후):
#   make regen-stats
#   make regen-stats-all
#
# 새 실험(experiment) 추가 (_EXPERIMENT_LABELS 등록 + 추론 완료 후):
#   make inference-all   ← 전체 데이터셋 추론 + manifest 갱신
#   make run             ← manifest 변경 자동 감지 → stats 재집계 후 App 실행
# =============================================================================

.PHONY: regen-attr
regen-attr:
	$(PYTHON) tools/generate_attrs.py --dataset $(DS)
	$(PYTHON) tools/precompute_panel_stats.py --dataset $(DS)

.PHONY: regen-attr-all
regen-attr-all:
	$(foreach ds,$(DATASETS),\
		$(PYTHON) tools/generate_attrs.py --dataset $(ds) && \
		$(PYTHON) tools/precompute_panel_stats.py --dataset $(ds) && ) true

.PHONY: regen-stats
regen-stats:
	$(PYTHON) tools/precompute_panel_stats.py --dataset $(DS) --force

.PHONY: regen-stats-all
regen-stats-all:
	$(PYTHON) tools/precompute_panel_stats.py --dataset seocho_2022 --force
	$(PYTHON) tools/precompute_panel_stats.py --dataset gangseo_2022 --force
	$(PYTHON) tools/precompute_panel_stats.py --dataset junggu_2022 --force
	$(PYTHON) tools/precompute_panel_stats.py --dataset jungrang_2022 --force
	$(PYTHON) tools/precompute_panel_stats.py --dataset mapo_2022 --force
	$(PYTHON) tools/precompute_panel_stats.py --dataset songpa_2022 --force
	$(PYTHON) tools/precompute_panel_stats.py --dataset suseo_2022 --force
	$(PYTHON) tools/precompute_panel_stats.py --dataset yangcheon_2022 --force
	$(PYTHON) tools/precompute_panel_stats.py --dataset youngdeungpo_2022 --force

# =============================================================================
# FiftyOne 캐시 강제 재빌드 (새 experiment 추가 또는 완전 재평가 필요 시)
#   make rebuild                       <- DS 기본값 데이터셋 캐시 삭제 후 재실행
#   make rebuild DS=coco-val-voc-50b
# =============================================================================
.PHONY: rebuild
rebuild:
	$(PYTHON) -c "import os; os.environ['FIFTYONE_PLUGINS_DIR']='plugins'; import fiftyone as fo; n='$(DS)'; fo.delete_dataset(n) if fo.dataset_exists(n) else None; print(f'Cleared FiftyOne cache: {n}')"
	$(PYTHON) main.py --dataset $(DS)

# =============================================================================
# 정리 타겟
#   make clean-stats    <- panel_stats.json 만 삭제 (regen-stats-all 전 강제 재실행용)
#   make clean-attrs    <- attrs + stats 삭제
#   make clean-all      <- data_dir 전체 삭제 (마스크·이미지 포함, 재다운로드 필요)
# =============================================================================
.PHONY: clean-stats
clean-stats:
	$(PYTHON) -c "\
import config; \
[__import__('pathlib').Path(config.DATASETS[ds]['data_dir']/'panel_stats.json').unlink(missing_ok=True) or print('rm',ds,'panel_stats.json') for ds in config.DATASETS]"

.PHONY: clean-attrs
clean-attrs:
	$(PYTHON) -c "\
import config; \
[(__import__('pathlib').Path(config.DATASETS[ds]['data_dir']/'sample_attrs.json').unlink(missing_ok=True), \
  __import__('pathlib').Path(config.DATASETS[ds]['data_dir']/'panel_stats.json').unlink(missing_ok=True)) for ds in config.DATASETS]"

.PHONY: clean-all
clean-all:
	$(PYTHON) -c "\
import config, shutil; \
[shutil.rmtree(str(config.DATASETS[ds]['data_dir']), ignore_errors=True) or print('rm', config.DATASETS[ds]['data_dir']) for ds in config.DATASETS]"
