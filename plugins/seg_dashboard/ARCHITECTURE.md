# Segmentation Dashboard -- Architecture Guide

This document defines the design philosophy and extension rules for the `seg_dashboard` plugin.
Follow these rules when adding new features so that anyone reading the code can understand it
and extend it with minimal file touches.

---

## 1. Core Principles

1. **No heavy computation at render time.**
   Mask/pixel operations, model inference, and evaluation aggregation all happen in
   `tools/precompute_panel_stats.py`. Panels read only `data/panel_stats.json`.
   If you see a pixel loop inside a panel, something is wrong.

2. **Single table (records) as the primary data source.**
   The per-sample unified table (`records`: one row = one sample's attributes + metrics)
   is the **sole** source for distributions, correlations, trend charts, and the data table.
   Think "pandas DataFrame" in JSON form.
   **Pixel-only exceptions** (cannot be derived from records — require pixel-level `report()`):
   `confusion_matrix`, `per_class`, `per_class_by_value`.
   No other precomputed stat blocks should exist; `fields` (old distribution cache) has been removed.

3. **Separate columns into `attribute` and `metric`.**
   - `attribute` = intrinsic data property, independent of predictions (e.g. `time`, `complexity`).
     **Only attributes are attached as fo.Dataset sample fields** (visible in the App sidebar).
   - `metric` = value derived from prediction/evaluation, differs per experiment
     (e.g. `recall`, `f1`, `precision`, `biou`).
     **Metrics exist only in panel_stats.json and are never fo.Dataset sample fields.**
     `dataset_builder.py` enforces this by checking `PANEL_COLUMN_META[key]["kind"]`.
   - Test: "Does the value change if you swap the prediction mask?" -> yes = metric, no = attribute.
     (`biou` is prediction-based, so it is a metric, NOT an attribute.)

4. **No hardcoding.** Class lists, field names, metric names, experiment names, and dataset keys
   are all read dynamically from stats/config.

5. **Missing data shows placeholder, not crash.** If a key is absent in stats, display a
   message instead of raising an exception. Old stats files must not break panels.

6. **All non-ASCII characters are forbidden in `fiftyone.yml`.** On Windows (cp949), FiftyOne's
   YAML parser silently fails on em-dashes, circled numbers, Korean text, etc. -- the plugin
   disappears from the App `+` menu with no error message. Keep `fiftyone.yml` strictly ASCII.

---

## 2. Layer Structure

```
Data layer      precompute_panel_stats.py  ->  panel_stats.json (columns / records schema)
     |  (read-only)
stats.py        load_stats(dataset?) + records / columns / fields / experiment helpers
     |
charts/         BaseChart subclasses -- return Plotly {"data","layout"} dict only.
                No FiftyOne import (numpy only). This allows offline unit testing.
     |
sections/       PanelSection subclasses -- group UI widgets (dropdowns/sliders) + charts.
     |
framework/      BasePanel -- state management + section loop + callback routing.
     |
panels/         5 concrete panels -- declare config + SECTIONS list only.
```

**Dependencies flow downward only.** Lower layers never import from higher layers.
Charts must not import FiftyOne -- this allows chart unit testing without launching an App.

---

## 3. Feature Addition Recipes

Each task is designed to touch the **minimum number of files**.

| What to add | What to do | Rebuild |
|-------------|------------|---------|
| **New chart** | `charts/<name>.py` with a `BaseChart` subclass -> 1-line import in `charts/__init__.py` | none |
| **New section** | `sections/<name>.py` with a `PanelSection` subclass -> 1-line import in `sections/__init__.py` | none |
| **New panel** | `panels/<name>.py` with a `BasePanel` subclass (config + SECTIONS) -> register in `__init__.py` + `fiftyone.yml` | none |
| **New attribute** (e.g. weather) | Add entry to `PANEL_COLUMN_META` with `kind:"attribute"` **and a `generate` key** (see Section 8). Then add the key to the desired group(s) in `ATTRIBUTE_GROUPS`. `generate_attrs.py` picks it up automatically -- no further code change. | `make regen-attr-all` |
| **New metric** (e.g. IoU) | Add entry to `PANEL_COLUMN_META` with `kind:"metric"` **and a `compute` key** (see Section 9). `precompute_panel_stats.py` picks it up via `_metric_specs()`; `list_metrics()` then exposes it to all dropdowns automatically -- no chart/panel code changes. New `source` strategy: add one function to `_MASK_FNS` or `_DERIVED_FNS`. | `make regen-stats-all` |
| **New experiment** (new model) | Add key to `config._EXPERIMENT_LABELS` **and** a loader to `MODEL_LOADERS` in `run_inference.py` (mismatch is auto-warned at startup). Run inference -> rebuild stats. No panel code changes. | `make inference` then `make regen-stats-all` |
| **New dataset** | Add entry to `config.DATASETS` with `"attributes": "<group>"` **and** add key to `DATASETS` variable in `Makefile`. Run full pipeline. Panel Dataset selector auto-discovers it when `panel_stats.json` exists. | `make pipeline DS=<name>` |

> Rule: **If adding a feature requires growing an `if/elif` chain in an existing file, reconsider the design.**
> Ideally: "new file + 1-line registration."

---

## 4. Component Contracts (Interfaces)

### BaseChart
```python
class BaseChart:
    field_types: tuple = ()              # supported column types ("categorical"/"numerical")
    def build_figure(self, stats, field=None, params=None) -> dict:
        # Always returns {"data": [...], "layout": {...}}.
        # No data -> return _empty_figure(msg).
```

### PanelSection
```python
class PanelSection(ABC):
    def render(self, panel, stats, state, callbacks=None) -> None:
        # Adds widgets/charts to panel. No return value.
        # state: current panel state dict.
        # callbacks: {"dataset":fn, "field":fn, "bins":fn, "metric":fn, "experiment":fn}
```

### BasePanel
```python
class BasePanel(foo.Panel):
    SECTIONS: list[PanelSection]         # declared by subclass
    STATE_DEFAULTS: dict                 # state schema (all set_state keys listed here)
    # on_load / render / callback routing provided by BasePanel.
    # Subclasses only declare PANEL_NAME, PANEL_LABEL, SECTIONS.
```

---

## 5. Data Schema Rules (panel_stats.json)

```jsonc
{
  "meta": {
    "dataset": str,
    "experiments": [str],
    "default_experiment": str,
    "experiment_labels": {exp: label}
  },
  "columns": {                          // drives all charts and the Schema panel
    "<col>": {"kind": "attribute"|"metric", "type": "categorical"|"numerical",
              "description": str, "values"|"range": ...}
                                        // populated from config.PANEL_COLUMN_META (see Section 9)
                                        // note: generate/compute keys are stripped before writing here
  },
  "experiments": {
    "<exp>": {
      "confusion_matrix": {"classes":[str], "matrix":[[int]]},  // pixel-level only
      "per_class":         {"<cls>": {"recall":f, "f1":f, "precision":f}},  // pixel-level only
      "per_class_by_value": {           // pixel-level only (categorical field -> per-class stats)
        "<field>": {"<value>": {"<cls>": {"recall":f, ...}}}
      },
      "records": [{"image_path":str, "time":str, "complexity":f, "count":int,
                   "recall":f, ...}],   // SINGLE PRIMARY SOURCE (attributes + all metrics)
      "correlation": {"fields":[], "metrics":[], "matrix":[[]], "n_samples":int}
    }
  }
}
```

- `records` — **the single primary source**. All distributions, correlations, and trend charts
  derive from this table at runtime. Attribute values come from `generate_attrs.py`;
  metric values are computed by `precompute_panel_stats.py` via the `compute` registry.
- `columns` — display-only metadata from `config.PANEL_COLUMN_META`. Never edit directly;
  edit `PANEL_COLUMN_META` instead. `generate`/`compute` keys are stripped before writing.
- Pixel-only blocks (`confusion_matrix`, `per_class`, `per_class_by_value`) — require
  FiftyOne `report()` and cannot be derived from records. No other stat blocks should exist.

---

## 6. Panel Layout

| Panel | Character | Key Sections |
|-------|-----------|--------------|
| (1) Data Analysis | attributes only (experiment-independent) | Dataset selector, attribute summary, distribution histograms |
| (2) Evaluation | metrics, per experiment | Dataset selector, experiment selector, confusion matrix |
| (3) Combined | attribute x metric | Dataset selector, experiment selector, metric breakdown, correlation heatmap |
| (4) Experiment | cross-experiment comparison | Dataset selector, experiment selector, Overall + per-class grouped bar |
| (5) Schema & Table | metadata | Dataset selector, column schema table, experiment selector, records table |

Note: In panel (4) the **Overall** bar is the mean of per-sample `records` values (macro average across
samples), while per-class bars come from pixel-level `report()`. They share the same y-axis but
use different aggregation methods -- this is intentional.

**Dataset selector** appears in all panels (global, independent of App grid).
**Experiment selector** appears only in panels (2)(3)(4) -- (1)(5) show data/schema, not metrics.

### Multi-Dataset Design
- `config.DATASETS` registry: each entry has `data_dir`, zoo download params, seeds.
- Each dataset has its own `data_dir/` containing `manifest.json`, `sample_attrs.json`,
  `panel_stats.json`, and mask subdirectories. Datasets are fully isolated on disk.
- Run the full pipeline for a new dataset: `make pipeline DS=<name>`
- The panel Dataset dropdown only lists datasets whose `panel_stats.json` actually exists.
  Switching datasets changes only the panel statistics -- the App grid stays on the dataset
  that was loaded by `main.py`. These two selections are **independent**.

### FiftyOne Dataset Lifecycle
- `run_inference.py` loads a raw zoo dataset (`coco-val-voc-50`) for GT mask extraction,
  then deletes it from FiftyOne DB after inference. Disk files are preserved in FiftyOne's
  zoo cache, so re-running inference does not re-download.
- `dataset_builder.build` creates `seg-eval-<name>` with `persistent=True`.
  Evaluation results (`seg_eval_<exp>`) are stored in FiftyOne's DB alongside the dataset.
- On subsequent `main.py` runs, `dataset_builder.build` detects the cached dataset and
  evaluation results → skips rebuild and re-evaluation entirely.
- `precompute_panel_stats.py` always passes `force_rebuild=True` since it needs fresh attrs.
- `main.py` startup cleanup removes stale `seg-eval-*` and any leftover zoo datasets,
  so the App shows only the two expected `seg-eval-*` datasets.
- To force a full rebuild: `make rebuild DS=<name>`

---

## 7. Anti-Patterns (Do Not Do)

- Mask/pixel computation inside a panel render function -> move to precompute.
- Hardcoded class names or metric names inside charts -> read from stats/columns dynamically.
- One long `panel.py` file that keeps growing -> split into sections and panels.
- Charts importing FiftyOne -> charts must use numpy only (FiftyOne dependency belongs in sections and above).
- Treating attributes and metrics the same -> always separate by `columns.kind`.
- Attaching a metric (biou, recall, ...) as a sample field -> dataset_builder blocks this;
  keep metrics in panel_stats.json only.
- Non-ASCII characters in `fiftyone.yml` -> use ASCII only (see Principle 6).
- Reading `stats["fields"]` directly -> the `fields` block no longer exists. Use `get_records()`.
- Hardcoding attribute names or generation logic in `generate_attrs.py` -> all attribute
  definitions live in `PANEL_COLUMN_META` (including the `generate` key); `generate_attrs.py`
  is data-driven and must not name individual attributes.
- Computing attribute values at render time -> attributes are pre-generated once by
  `generate_attrs.py` and stored in `sample_attrs.json`; panels only read from `panel_stats.json`.
- Calling `configure_sidebar()` only once for the active dataset -> call it **inside** the
  `_build_all_datasets` loop while each dataset's `activate_dataset()` is in effect, so that
  datasets with the same attribute group automatically receive identical sidebar layouts.
- Hardcoding metric names in a `SUPPORTED_METRICS` constant -> use `list_metrics(stats)`,
  which reads `columns` dynamically; the dropdown stays in sync with `config.py` automatically.

---

## 8. Attribute Rule Groups + Dataset Attachment

Attributes flow through three layers:

```
PANEL_COLUMN_META          — rule library: all possible attributes with generate specs
       |
ATTRIBUTE_GROUPS           — named presets: {"basic": [...], "full": [...], ...}
       |
DATASETS[name]["attributes"]  — each dataset picks a group name
       |
config.dataset_attribute_keys(name)  — resolves group -> validated key list
       |
generate_attrs.py          — generates only those keys for this dataset
       |
sample_attrs.json / dataset fields / panel_stats columns  — propagate automatically
```

To use different attributes per dataset: add/modify entries in `ATTRIBUTE_GROUPS` and
set `"attributes": "<group>"` in the dataset's `DATASETS` entry. No other code changes needed.

Adding a new attribute that should appear in all datasets: register it in `PANEL_COLUMN_META`,
then add its key to the relevant group(s) in `ATTRIBUTE_GROUPS`.

### Sidebar auto-derivation

**Same attribute group → identical sidebar layout, automatically.**

`configure_sidebar(dataset)` in `pipeline/app.py` builds sidebar groups from the actual schema
fields and `config.EXPERIMENTS` -- no hardcoded field names. It is called **inside** the
`_build_all_datasets` loop in `main.py` while each dataset's `activate_dataset()` is still in
effect. As a result:

- Datasets in the same attribute group automatically get the same sidebar group structure.
- Changing an attribute group name (or switching a dataset to a different group) changes the
  sidebar without any other code edits.

To customize sidebar grouping, edit only `configure_sidebar()` in `pipeline/app.py`.

### Known limitation: global activation model

`config.activate_dataset(name)` mutates module-level globals (`DATA_DIR`, `EXPERIMENTS`, etc.).
`main.py` processes multiple datasets in one process, so **all per-dataset work must run inside
the loop while that dataset's globals are active**. If you add a step that reads config globals
outside the loop, it will silently use the last-activated dataset's values.

Workaround: keep every dataset-specific operation inside `_build_all_datasets`. If you need
parallel processing, snapshot the relevant globals into local variables before any `activate_dataset`
call that might change them.

---

## 9. PANEL_COLUMN_META -- Attribute Schema Design

`config.PANEL_COLUMN_META` is the **rule library** for every column that appears
in the dashboard -- both attributes and metrics. Attributes are also registered in
`ATTRIBUTE_GROUPS` to control which datasets use them (see Section 8).

### Attribute entry structure
```python
"<field_name>": {
    "kind":        "attribute",
    "type":        "categorical" | "numerical",
    "description": str,                    # shown in Schema panel
    "values":      [str, ...],             # categorical only -- also used for generation
    "range":       [lo, hi],               # numerical only  -- also used for generation
    "generate":    {                       # controls generate_attrs.py
        "method": "choice" | "float" | "int",
        "round":  int,                     # float only (decimal places, default 3)
    },
}
```

`generate.method` rules:
| method | formula | extra keys |
|--------|---------|------------|
| `"choice"` | `rng.choice(values)` | — |
| `"float"` | `round(rng.uniform(*range), round)` | `round` (default 3) |
| `"int"` | `rng.randint(*range)` | — |

**Seed isolation**: each attribute gets its own RNG seeded with `f"{ATTR_SEED}:{field}"`.
Adding a new attribute never changes the generated values of existing attributes.

**`generate` key is stripped before writing to `panel_stats.json`.**
It is internal config for `generate_attrs.py` only and must not appear in the output stats file.
`precompute_panel_stats.py` copies only `{kind, type, description, values, range}` into `columns`.

**`sample_attrs.json` is fully overwritten** (not merged) on each `generate_attrs.py` run.
Attributes removed from `PANEL_COLUMN_META` are automatically cleaned up from the file.

### Metric entry structure
```python
"<field_name>": {
    "kind":        "metric",
    "type":        "numerical",
    "description": str,
    "range":       [lo, hi],               # optional, for display hints
    "compute":     {                       # controls precompute_panel_stats.py
        "source": "fiftyone_eval"          # read field from FiftyOne evaluation result
               | "mask"                   # compute from raw mask files
               | "derived",               # compute from other metrics already in records
        "field":  str,                     # fiftyone_eval only -- fo eval field name
        "fn":     str,                     # mask/derived -- key in _MASK_FNS/_DERIVED_FNS
        "deps":   [str, ...],              # derived only -- names of already-computed metrics
                                           # passed as positional args (in order) to the fn
        "params": dict,                    # mask only -- extra kwargs passed to the fn
    },
}
```
`compute` is parallel to attribute `generate`: it tells `precompute_panel_stats.py` **how** to
compute this metric without hardcoding per-metric logic inside the script.
The key is stripped before writing to `panel_stats.json` (display metadata only in `columns`).

**compute source strategies**:
| source | where computed | dispatch dict |
|--------|---------------|---------------|
| `fiftyone_eval` | FiftyOne `evaluate_segmentations` result | n/a (direct field read) |
| `mask` | `_MASK_FNS[fn](manifest, exp, **params)` | `_MASK_FNS` |
| `derived` | `_DERIVED_FNS[fn](p, r, **params)` per sample | `_DERIVED_FNS` |

New `source` or `fn` value: add one entry to the corresponding dispatch dict.
No `if/elif` chain needed.

### Makefile update commands

| Changed in `config.py` | Command |
|------------------------|---------|
| New / modified attribute | `make regen-attr-all` |
| New / modified metric | `make regen-stats-all` |
| New experiment | `make inference` then `make regen-stats-all` |
| New dataset | add to `config.DATASETS` **and** `DATASETS` var in `Makefile`, then `make pipeline DS=<name>` |
