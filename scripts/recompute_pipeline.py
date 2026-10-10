# -*- coding: utf-8 -*-
"""
المسار الموحد الكامل — من الملفين الخامين إلى كل أرقام الورقة.

المدخلات : curated_986_dataset.csv  +  transformed_dataset.csv (984)
المخرجات : جدول وصفي · تقرير استدلالي · تفكيك MI · فحوص سلامة · ملف CSV نهائي

لماذا مسار واحد: الأرقام مرّت سابقاً عبر ثلاثة سكربتات منفصلة بأدوات قياس
مختلفة، فنتج تعارض في ΔNLOC (−9.797 مقابل −2.049) وانقلاب إشارة في ΔCD و ΔMI.
هنا كل مقياس يُحسب مرة واحدة بأداة واحدة تُطبَّق على الطرفين بالطريقة نفسها،
فالتعارض مستحيل بنيوياً. هذا الملف هو حزمة إعادة الإنتاج للورقة (الملاحظة 14).

تعريفات القياس المعتمدة — تُنقل حرفياً إلى القسم 3.4:
  CC      : radon ComplexityVisitor.total_complexity (يشمل الدوال المتداخلة)
  NLOC    : radon raw.analyze().sloc
  CD      : CC / NLOC
  MI      : radon mi_visit (count_multi=True)، مقصوصة في [0, 100]
  Volume  : radon Halstead total.volume
  Cognitive: custom AST score adapted from Campbell; not validated SonarSource equivalence
  المتغيران "المنسّقان" لـ NLOC و CD: بعد توحيد التنسيق بـ black لعزل أثر
  اصطلاحات الأسطر عن التغير البنيوي.

المتطلبات:  pip install -q radon black
"""

import os
import ast
import math
import textwrap
import numpy as np
import pandas as pd
from scipy import stats
from scipy.stats import rankdata

import black
from radon.raw import analyze as raw_analyze
from radon.metrics import mi_visit, mi_parameters, mi_compute, h_visit
from radon.complexity import ComplexityVisitor

from pathlib import Path
import argparse
parser = argparse.ArgumentParser(description="Remeasure archived function pairs; no API calls.")
parser.add_argument("--data-dir", type=Path, default=Path(__file__).resolve().parents[1] / "data")
parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parents[1] / "outputs")
args = parser.parse_args()
args.output_dir.mkdir(parents=True, exist_ok=True)
SAVE_DIR = str(args.data_dir)


CURATED_CSV     = os.path.join(SAVE_DIR, "curated_986_dataset.csv")
TRANSFORMED_CSV = os.path.join(SAVE_DIR, "transformed_dataset.csv")
OUTPUT_CSV = str(args.output_dir / "pipeline_final_metrics.csv")
EXCLUDED_CSV = str(args.output_dir / "pipeline_excluded_pairs.csv")

NLOC_MIN, NLOC_MAX = 5, 60
CC_MIN,   CC_MAX   = 3, 40
K = 100.0 / 171.0
BLACK_MODE = black.Mode()


# ──────────────────────────────────────────────────────────────────────────────
# Custom cognitive score adapted from Campbell; see methodological limits
# ──────────────────────────────────────────────────────────────────────────────
class CognitiveComplexity(ast.NodeVisitor):
    """
    القواعد المطبقة:
      +1 مع عقوبة تداخل : if · for · while · async for · معالج except · التعبير الشرطي
      +1 بلا عقوبة تداخل: elif · else · else الخاصة بحلقة · كل تسلسل عوامل منطقية
      تداخل بلا نقاط    : أجسام ما سبق · lambda · الاستيعابات
      Nested FunctionDef bodies are visited without a new nesting increment.
      +1 لكل استدعاء ذاتي باسم الدالة المحيطة.
    `elif` في شجرة Python هو If داخل orelse؛ يُميَّز عن `else: if` بتساوي col_offset.
    """

    def __init__(self, own_name=None):
        self.score = 0
        self.nesting = 0
        self.own_name = own_name

    def _body(self, stmts):
        self.nesting += 1
        for s in stmts:
            self.visit(s)
        self.nesting -= 1

    def visit_If(self, node):
        self._handle_if(node, is_elif=False)

    def _handle_if(self, node, is_elif):
        self.score += 1 if is_elif else 1 + self.nesting
        self.visit(node.test)
        self._body(node.body)
        orelse = node.orelse
        if (len(orelse) == 1 and isinstance(orelse[0], ast.If)
                and orelse[0].col_offset == node.col_offset):
            self._handle_if(orelse[0], is_elif=True)
        elif orelse:
            self.score += 1
            self._body(orelse)

    def visit_IfExp(self, node):
        self.score += 1 + self.nesting
        self.visit(node.test)
        self._body([node.body, node.orelse])

    def _loop(self, node):
        self.score += 1 + self.nesting
        for f in ("iter", "test"):
            if hasattr(node, f):
                self.visit(getattr(node, f))
        self._body(node.body)
        if node.orelse:
            self.score += 1
            self._body(node.orelse)

    visit_For = visit_AsyncFor = visit_While = _loop

    def visit_Try(self, node):
        for s in node.body:
            self.visit(s)
        for h in node.handlers:
            self.score += 1 + self.nesting
            self._body(h.body)
        if node.orelse:
            self.score += 1
            self._body(node.orelse)
        for s in node.finalbody:
            self.visit(s)

    visit_TryStar = visit_Try

    def visit_BoolOp(self, node):
        self.score += 1
        self.generic_visit(node)

    def visit_Lambda(self, node):
        self.nesting += 1
        self.generic_visit(node)
        self.nesting -= 1

    def _comprehension(self, node):
        self.nesting += 1
        for gen in node.generators:
            for cond in gen.ifs:
                self.score += 1 + self.nesting
                self.visit(cond)
            self.visit(gen.iter)
        for f in ("elt", "key", "value"):
            if hasattr(node, f):
                self.visit(getattr(node, f))
        self.nesting -= 1

    visit_ListComp = visit_SetComp = visit_DictComp = visit_GeneratorExp = _comprehension

    def visit_Call(self, node):
        name = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
        if self.own_name and name == self.own_name:
            self.score += 1
        self.generic_visit(node)


# ──────────────────────────────────────────────────────────────────────────────
# قياس نسخة واحدة من الكود
# ──────────────────────────────────────────────────────────────────────────────
def measure(code_str):
    """يعيد قاموس المقاييس لنسخة واحدة، أو يرفع استثناء إن تعذر التحليل."""
    src = textwrap.dedent(str(code_str)).strip()
    tree = ast.parse(src)

    own = next((n.name for n in ast.walk(tree)
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))), None)
    cog = CognitiveComplexity(own_name=own)
    cog.visit(tree)

    raw = raw_analyze(src)
    cc = ComplexityVisitor.from_ast(tree).total_complexity
    vol = h_visit(src).total.volume
    volume_, cc_, lloc_, comments_pct = mi_parameters(src, count_multi=True)

    nloc = raw.sloc
    return {
        "cc": cc,
        "nloc": nloc,
        "cd": (cc / nloc) if nloc else np.nan,
        "mi": mi_visit(src, multi=True),
        "mi_neutral": mi_compute(volume_, cc_, lloc_, 0.0),
        "cognitive": cog.score,
        "volume": vol,
        "lloc": lloc_,
        "comments_pct": comments_pct,
        "_src": src,
    }


def formatted_metrics(src):
    """NLOC و CD بعد توحيد التنسيق؛ يرفع استثناء إن فشل black."""
    fmt = black.format_str(src, mode=BLACK_MODE)
    raw = raw_analyze(fmt)
    cc = ComplexityVisitor.from_code(fmt).total_complexity
    return raw.sloc, (cc / raw.sloc if raw.sloc else np.nan)


# ──────────────────────────────────────────────────────────────────────────────
# 1. التحميل والدمج
# ──────────────────────────────────────────────────────────────────────────────
df_cur = pd.read_csv(CURATED_CSV)
df_tr  = pd.read_csv(TRANSFORMED_CSV)
print(f"curated: {len(df_cur)}   transformed: {len(df_tr)}")
assert df_tr["func_id"].duplicated().sum() == 0, "معرفات مكررة في ملف التحويل"

df = df_cur[["func_id", "domain", "code"]].merge(
    df_tr[["func_id", "transformed_code", "model_version"]],
    on="func_id", how="inner", validate="one_to_one")
print(f"أزواج مرشحة للقياس: {len(df)}")
print("-" * 76)


# ──────────────────────────────────────────────────────────────────────────────
# 2. القياس زوجاً زوجاً
# ──────────────────────────────────────────────────────────────────────────────
records, excluded = [], []

for _, r in df.iterrows():
    fid = r["func_id"]
    try:
        pre = measure(r["code"])
    except Exception as e:
        excluded.append({"func_id": fid, "domain": r["domain"],
                         "stage": "pre_parse", "reason": f"{type(e).__name__}: {e}"})
        continue
    try:
        post = measure(r["transformed_code"])
    except Exception as e:
        excluded.append({"func_id": fid, "domain": r["domain"],
                         "stage": "post_parse", "reason": f"{type(e).__name__}: {e}"})
        continue
    try:
        pre_fmt_nloc,  pre_fmt_cd  = formatted_metrics(pre["_src"])
        post_fmt_nloc, post_fmt_cd = formatted_metrics(post["_src"])
    except Exception as e:
        excluded.append({"func_id": fid, "domain": r["domain"],
                         "stage": "black", "reason": f"{type(e).__name__}: {str(e)[:120]}"})
        continue

    rec = {"func_id": fid, "domain": r["domain"], "model_version": r["model_version"]}
    for k in ("cc", "nloc", "cd", "mi", "mi_neutral", "cognitive",
              "volume", "lloc", "comments_pct"):
        rec[f"pre_{k}"], rec[f"post_{k}"] = pre[k], post[k]
        rec[f"delta_{k}"] = post[k] - pre[k]
    rec["pre_fmt_nloc"],  rec["post_fmt_nloc"]  = pre_fmt_nloc, post_fmt_nloc
    rec["pre_fmt_cd"],    rec["post_fmt_cd"]    = pre_fmt_cd,   post_fmt_cd
    rec["delta_fmt_nloc"] = post_fmt_nloc - pre_fmt_nloc
    rec["delta_fmt_cd"]   = post_fmt_cd   - pre_fmt_cd

    # تفكيك ΔMI إلى حدوده الأربعة
    lv0 = math.log(pre["volume"])  if pre["volume"]  > 0 else 0.0
    lv1 = math.log(post["volume"]) if post["volume"] > 0 else 0.0
    ll0 = math.log(pre["lloc"])    if pre["lloc"]    > 0 else 0.0
    ll1 = math.log(post["lloc"])   if post["lloc"]   > 0 else 0.0
    cterm = lambda p: 50.0 * math.sin(math.sqrt(2.46 * math.radians(p)))
    rec["term_volume"]   = K * (-5.2)  * (lv1 - lv0)
    rec["term_cc"]       = K * (-0.23) * (post["cc"] - pre["cc"])
    rec["term_lloc"]     = K * (-16.2) * (ll1 - ll0)
    rec["term_comments"] = K * (cterm(post["comments_pct"]) - cterm(pre["comments_pct"]))
    records.append(rec)

d = pd.DataFrame(records)
ex = pd.DataFrame(excluded)
N = len(d)

print(f"أزواج مقيسة بنجاح : {N}")
if len(ex):
    print(f"أزواج مستبعدة      : {len(ex)}")
    print(ex.groupby(["stage"]).size().to_string())
    print("\nالمستبعد حسب المجال والمرحلة:")
    print(ex.groupby(["domain", "stage"]).size().to_string())
    ex.to_csv(EXCLUDED_CSV, index=False)
print("-" * 76)


# ──────────────────────────────────────────────────────────────────────────────
# 3. الجدول الوصفي
# ──────────────────────────────────────────────────────────────────────────────
def ci_str(x):
    lo, hi = stats.t.interval(0.95, df=len(x) - 1, loc=np.mean(x), scale=stats.sem(x))
    return f"[{lo:+.3f}, {hi:+.3f}]"


SPEC = [
    ("CC",                   "cc"),
    ("NLOC",                 "nloc"),
    ("NLOC (formatted)",     "fmt_nloc"),
    ("CD",                   "cd"),
    ("CD (formatted)",       "fmt_cd"),
    ("Cognitive Complexity", "cognitive"),
    ("Halstead Volume",      "volume"),
    ("Comments %",           "comments_pct"),
    ("MI",                   "mi"),
    ("MI (comment-neutral)", "mi_neutral"),
]

rows = []
for label, key in SPEC:
    pre, post = d[f"pre_{key}"], d[f"post_{key}"]
    dd = d[f"delta_{key}"].to_numpy(float)
    rows.append({
        "Metric": label,
        "Mean pre": round(pre.mean(), 3),
        "Mean post": round(post.mean(), 3),
        "Mean Δ": round(dd.mean(), 4),
        "Median Δ": round(float(np.median(dd)), 4),
        "95% CI": ci_str(dd),
        "Rel %": round(dd.mean() / pre.mean() * 100, 2) if pre.mean() else np.nan,
        "↓/=/↑": f"{int((dd<0).sum())}/{int((dd==0).sum())}/{int((dd>0).sum())}",
    })

print("=" * 76)
print(f"DESCRIPTIVE SUMMARY — N = {N}")
print("=" * 76)
print(pd.DataFrame(rows).to_string(index=False))
print()


# ──────────────────────────────────────────────────────────────────────────────
# 4. الاستدلال
# ──────────────────────────────────────────────────────────────────────────────
def pratt_wilcoxon(x):
    x = np.asarray(x, float)
    n, n0 = x.size, int((x == 0).sum())
    r = rankdata(np.abs(x))
    w = float(r[x > 0].sum())
    mu = (n * (n + 1) - n0 * (n0 + 1)) / 4.0
    var = (n * (n + 1) * (2 * n + 1) - n0 * (n0 + 1) * (2 * n0 + 1)) / 24.0
    _, c = np.unique(np.abs(x[x != 0]), return_counts=True)
    var -= float((c ** 3 - c).sum()) / 48.0
    z = (w - mu) / math.sqrt(var)
    return w, z, 2.0 * stats.norm.sf(abs(z))


def hodges_lehmann(x):
    x = np.asarray(x, float)
    w = (x[:, None] + x[None, :]) / 2.0
    return float(np.median(w[np.triu_indices(x.size)]))


print("=" * 76)
print(f"INFERENTIAL REPORT — Wilcoxon signed-rank (Pratt), N = {N}")
print("=" * 76)
print(f"{'Metric':<24}{'W+':>12}{'Z':>10}{'p':>13}{'r':>8}{'HL':>9}{'↓/=/↑':>18}")
print("-" * 76)
for label, key in [("ΔCC", "cc"), ("ΔCognitive", "cognitive"),
                   ("ΔMI", "mi"), ("ΔMI comment-neutral", "mi_neutral"),
                   ("ΔCD (formatted)", "fmt_cd")]:
    x = d[f"delta_{key}"].to_numpy(float)
    w, z, p = pratt_wilcoxon(x)
    hl = hodges_lehmann(x)
    split = f"{int((x<0).sum())}/{int((x==0).sum())}/{int((x>0).sum())}"
    print(f"{label:<24}{w:>12.1f}{z:>10.3f}{p:>13.2e}"
          f"{abs(z)/math.sqrt(N):>8.3f}{hl:>9.3f}{split:>18}")
print("=" * 76)
print("ملاحظة: حين يكون وسيط الفروق صفراً، تُقرأ r دليلاً على اتساق اتجاه الرتب")
print("لا على حجم التغير النمطي، وتُذكر هذه القراءة ملتصقة بالرقم في الورقة.")
print()


# ──────────────────────────────────────────────────────────────────────────────
# 5. تفكيك ΔMI
# ──────────────────────────────────────────────────────────────────────────────
print("=" * 76)
print("MI DECOMPOSITION")
print("=" * 76)
print(f"{'الحد':<34}{'متوسط المساهمة':>16}{'95% CI':>24}")
print("-" * 76)
for col, lab in [("term_volume", "Halstead Volume"), ("term_cc", "Cyclomatic Complexity"),
                 ("term_lloc", "Logical Lines of Code"), ("term_comments", "Comments / docstrings")]:
    x = d[col].to_numpy(float)
    print(f"{lab:<34}{x.mean():>+16.3f}{ci_str(x):>24}")
tot = d[["term_volume", "term_cc", "term_lloc", "term_comments"]].sum(axis=1).to_numpy(float)
print("-" * 76)
print(f"{'Formal sum (zero-log convention)':<34}{tot.mean():>+16.3f}{ci_str(tot):>24}")
print(f"{'ΔMI الرسمية':<34}{d['delta_mi'].mean():>+16.3f}{ci_str(d['delta_mi'].to_numpy(float)):>24}")
print(f"{'ΔMI محايدة التعليقات':<34}{d['delta_mi_neutral'].mean():>+16.3f}"
      f"{ci_str(d['delta_mi_neutral'].to_numpy(float)):>24}")

had = int((d["pre_comments_pct"] > 0).sum())
lost = int(((d["pre_comments_pct"] > 0) & (d["post_comments_pct"] == 0)).sum())
print(f"\nدوال فقدت توثيقها بالكامل: {lost} من {had} كانت تحتويه ({lost/max(1,had)*100:.1f}%)")
print("\nΔMI محايدة التعليقات حسب المجال:")
print(d.groupby("domain")["delta_mi_neutral"].agg(["count", "mean", "median"]).round(3).to_string())
print()


# ──────────────────────────────────────────────────────────────────────────────
# 6. فحوص السلامة
# ──────────────────────────────────────────────────────────────────────────────
print("=" * 76)
print("INTEGRITY CHECKS")
print("=" * 76)
over = d[d["pre_nloc"] > NLOC_MAX]
print(f"دوال أصلية تتجاوز NLOC = {NLOC_MAX}: {len(over)}")
bad = d[(d["pre_cc"] < CC_MIN) | (d["pre_cc"] > CC_MAX)]
print(f"دوال أصلية خارج مدى CC = {CC_MIN}–{CC_MAX}: {len(bad)}")

sat_pre  = int(((d["pre_mi"]  >= 99.999) | (d["pre_mi"]  <= 0.001)).sum())
sat_post = int(((d["post_mi"] >= 99.999) | (d["post_mi"] <= 0.001)).sum())
print(f"MI عند حدّي المقياس: قبل {sat_pre} ({sat_pre/N*100:.1f}%) · "
      f"بعد {sat_post} ({sat_post/N*100:.1f}%)")

print("\nتدفق الترشيح حسب المجال:")
flow = pd.DataFrame({
    "curated": df_cur["domain"].value_counts(),
    "transformed": df_tr["domain"].value_counts(),
    "measured": d["domain"].value_counts(),
}).fillna(0).astype(int)
flow["بقاء %"] = (flow["measured"] / flow["curated"] * 100).round(1)
print(flow.to_string())
spread = flow["بقاء %"].max() - flow["بقاء %"].min()
print(f"\nتفاوت معدلات البقاء بين المجالات: {spread:.1f} نقطة مئوية")
print("   ← تفاوت يتجاوز نحو 10 نقاط يستوجب ذكره في Threats to Validity.")

print(f"\nلقطات النموذج: {d['model_version'].value_counts().to_dict()}")
print("=" * 76)

d.to_csv(OUTPUT_CSV, index=False)
print(f"\nحُفظ: {OUTPUT_CSV}")
if len(ex):
    print(f"حُفظ المستبعد: {EXCLUDED_CSV}")