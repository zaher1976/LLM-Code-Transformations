from pathlib import Path
import argparse
parser = argparse.ArgumentParser(description="Recompute ablation metrics from archived generations; no API calls.")
parser.add_argument("--data-dir", type=Path, default=Path(__file__).resolve().parents[1] / "data")
parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parents[1] / "outputs")
args = parser.parse_args()
args.output_dir.mkdir(parents=True, exist_ok=True)
SAVE_DIR = str(args.data_dir)
import os, ast, textwrap, numpy as np, pandas as pd
from scipy import stats
from radon.raw import analyze as raw_analyze
from radon.metrics import mi_visit, mi_parameters, mi_compute
from radon.complexity import ComplexityVisitor

BASE_CSV   = os.path.join(SAVE_DIR, "pipeline_final_metrics.csv")
CURATED_CSV= os.path.join(SAVE_DIR, "curated_986_dataset.csv")
OUT_CSV    = os.path.join(SAVE_DIR, "ablation_transformed.csv")
RESULT_CSV = str(args.output_dir / "ablation_results.csv")

def measure(code_str):
    src = textwrap.dedent(str(code_str)).strip(); ast.parse(src)
    raw = raw_analyze(src)
    cc  = ComplexityVisitor.from_code(src).total_complexity
    v, c, l, cm = mi_parameters(src, count_multi=True)
    return {"cc": cc, "nloc": raw.sloc, "comments_pct": cm,
            "mi": float(mi_visit(src, multi=True)), "mi_neutral": mi_compute(v, c, l, 0.0)}

base = pd.read_csv(BASE_CSV).drop(columns=["model_version"], errors="ignore")   # ← الإصلاح
abl  = pd.read_csv(OUT_CSV)
cur  = pd.read_csv(CURATED_CSV)[["func_id", "code"]]
MODEL_USED = abl["model_version"].unique().tolist()

d = (base.merge(abl[["func_id", "transformed_code"]], on="func_id")
         .merge(cur, on="func_id"))
print(f"أزواج داخلة في التحليل: {len(d)} · لقطة النموذج: {MODEL_USED}")

rows, skipped = [], 0
for _, r in d.iterrows():
    try:
        pre, a = measure(r["code"]), measure(r["transformed_code"])
    except Exception:
        skipped += 1; continue
    rows.append({"func_id": r["func_id"], "domain": r["domain"],
                 "pre_comments": pre["comments_pct"],
                 "orig_comments": r["post_comments_pct"], "abl_comments": a["comments_pct"],
                 "orig_cc": r["post_cc"],   "abl_cc": a["cc"],
                 "orig_mi": r["post_mi"],   "abl_mi": a["mi"],
                 "orig_mi0": r["post_mi_neutral"], "abl_mi0": a["mi_neutral"]})
m = pd.DataFrame(rows); N = len(m)
if skipped: print(f"تخطّي {skipped} زوجاً تعذّر قياسه")

m["orig_lost"] = (m["pre_comments"] > 0) & (m["orig_comments"] == 0)
m["abl_lost"]  = (m["pre_comments"] > 0) & (m["abl_comments"] == 0)
a_ = int(( m["orig_lost"] &  m["abl_lost"]).sum())
b_ = int(( m["orig_lost"] & ~m["abl_lost"]).sum())
c_ = int((~m["orig_lost"] &  m["abl_lost"]).sum())
d_ = int((~m["orig_lost"] & ~m["abl_lost"]).sum())
p_mc = min(1.0, 2*stats.binom.cdf(min(b_, c_), b_+c_, 0.5)) if (b_+c_) else 1.0

def ci(v):
    v = np.asarray(v, float)
    lo, hi = stats.t.interval(0.95, df=len(v)-1, loc=v.mean(), scale=stats.sem(v))
    return v.mean(), lo, hi

print("\n" + "="*72)
print(f"PROMPT ABLATION — N = {N}")
print("="*72)
print(f"فقدان التوثيق بالبرومبت الأصلي : {m['orig_lost'].mean()*100:5.1f}%  ({int(m['orig_lost'].sum())}/{N})")
print(f"فقدان التوثيق بالبرومبت المعدّل: {m['abl_lost'].mean()*100:5.1f}%  ({int(m['abl_lost'].sum())}/{N})")
print("-"*72)
print(f"McNemar: فقدت دائماً {a_} · فقدت ثم حُفظت {b_} · حُفظت ثم فقدت {c_} · سليمة دائماً {d_}")
print(f"p (ثنائي الحدين المضبوط) = {p_mc:.3e}")
print("-"*72)
for lab, o, a2 in [("كثافة التعليقات %","orig_comments","abl_comments"),
                   ("Cyclomatic Complexity","orig_cc","abl_cc"),
                   ("Maintainability Index","orig_mi","abl_mi"),
                   ("MI محايدة التعليقات","orig_mi0","abl_mi0")]:
    diff = (m[a2] - m[o]).to_numpy(float)
    mu, lo, hi = ci(diff)
    pw = f"{stats.wilcoxon(diff, zero_method='pratt').pvalue:.2e}" if np.any(diff != 0) else "—"
    print(f"{lab:<24} المعدّل − الأصلي = {mu:+8.3f}  [{lo:+.3f}, {hi:+.3f}]   Wilcoxon p = {pw}")
print("="*72)
m.to_csv(RESULT_CSV, index=False); print(f"حُفظ: {RESULT_CSV}")