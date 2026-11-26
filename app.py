import streamlit as st
import pandas as pd
from features import feature_frame
from model_io import load_bundle
import json
import sys
from importlib.metadata import version
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
st.set_page_config(page_title="PhishGuard | URL Intelligence", page_icon="🛡️", layout="wide")
st.markdown(f"<style>{(ROOT / 'style.css').read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)

@st.cache_resource
def load_models():
    env_path = ROOT / "model_environment.json"
    if env_path.exists():
        env = json.loads(env_path.read_text(encoding="utf-8"))
        actual_python = f"{sys.version_info.major}.{sys.version_info.minor}"
        if actual_python != env["python"]:
            raise RuntimeError(f"Use Python {env['python']} (model export runtime), not {actual_python}.")
        for package, expected in env["packages"].items():
            if version(package) != expected:
                raise RuntimeError(f"Install {package}=={expected} to match the model export.")
    return load_bundle(ROOT / "models.pkl")

try:
    models, columns = load_models()
except Exception as error:
    st.error("Could not load the bundled models. Install the pinned dependencies and use the Python version of the original export. See the README for troubleshooting.")
    st.code(str(error))
    st.stop()

# Use exactly the same features and preprocessing as the training notebook.
def scan_url(url):
    url = url.strip()
    if len(url) > 8192:
        raise ValueError("URL is too long (maximum 8,192 characters).")
    parsed = urlsplit(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError("Enter a complete HTTP or HTTPS URL.")
    data = feature_frame(url, columns)
    predictions = {name: int(model.predict(data)[0]) for name, model in models.items()}
    return data, predictions

st.markdown('''<div class="pg-nav"><span class="pg-logo">◈</span><strong>PHISH<span>GUARD</span></strong><span class="pg-nav-end">URL INTELLIGENCE / 2026</span></div>
<div class="pg-hero"><div class="pg-eyebrow">CYBERSECURITY · DATA MINING PROJECT</div><h1>Know your link.<br><span>Before you click.</span></h1><p>Analyze URL characteristics and compare three trained classification algorithms without opening the website.</p><div class="pg-tags"><span>◉ URL-only analysis</span><span>◉ No website requests</span><span>◉ Educational prototype</span></div></div>''', unsafe_allow_html=True)

a, b, c, d = st.columns(4)
a.metric("SOURCE RECORDS", "235,795", help="Original PhiUSIIL dataset size before cleaning.")
b.metric("TRAINED MODELS", len(models))
c.metric("INPUT FEATURES", len(columns))
d.metric("OUTPUT CLASSES", 2)

scanner, performance, about = st.tabs(["01  /  URL Scanner", "02  /  Model Performance", "03  /  Project Overview"])
with scanner:
    left, right = st.columns([1, 1], gap="large")
    with left:
        st.subheader("Analyze a URL")
        st.caption("Enter a complete URL. The scanner analyzes its text only.")
        with st.form("scanner"):
            url = st.text_input("Website URL", placeholder="https://example.com", max_chars=8192)
            selected = st.selectbox("Primary classification model", list(models))
            submitted = st.form_submit_button("Analyze website  →", type="primary", use_container_width=True)
        if submitted:
            st.session_state.pop("scan_result", None)
            try:
                data, predictions = scan_url(url)
                st.session_state["scan_result"] = (data, predictions, selected)
            except ValueError as error:
                st.warning(str(error))
            except Exception as error:
                st.error("The model could not analyze this input.")
                st.code(str(error))
        st.markdown('''<div class="pg-note"><strong>URL-ONLY ANALYSIS</strong><br>This application does not open or fetch the submitted website. Avoid entering links that contain passwords, access tokens or other sensitive information.</div>''', unsafe_allow_html=True)
    with right:
        st.subheader("Detection result")
        result = st.session_state.get("scan_result")
        if result is None:
            st.markdown('''<div class="pg-empty"><div class="pg-radar">◎</div><h3>Ready to scan</h3><p>Your classification will appear here.</p></div>''', unsafe_allow_html=True)
        else:
            data, predictions, selected = result
            is_phishing = predictions[selected] == 1
            if is_phishing:
                st.markdown('<div class="pg-result pg-danger"><div>⚠ &nbsp; CLASSIFICATION COMPLETE</div><h2>PHISHING WEBSITE</h2><p>The selected model predicts a phishing URL.</p></div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="pg-result pg-safe"><div>✓ &nbsp; CLASSIFICATION COMPLETE</div><h2>LEGITIMATE WEBSITE</h2><p>The selected model predicts a legitimate URL.</p></div>', unsafe_allow_html=True)
            st.caption(f"Primary model: {selected} · Model prediction, not a verified safety verdict.")
            st.subheader("Model comparison")
            for col, (name, prediction) in zip(st.columns(len(predictions)), predictions.items()):
                with col:
                    if prediction == 1:
                        st.error(f"{name}\n\nPhishing")
                    else:
                        st.success(f"{name}\n\nLegitimate")
            if len(set(predictions.values())) > 1:
                st.warning("The models disagree on this URL.")
    if result is not None:
        st.divider()
        st.subheader("Extracted URL features")
        features = result[0].iloc[0]
        for col, key, label in zip(st.columns(4), ["URL_Length", "URL_Entropy", "HTTPS", "Path_Depth"], ["URL length", "Character entropy", "HTTPS in URL", "Path depth"]):
            value = features[key]
            col.metric(label, ("Yes" if value else "No") if key == "HTTPS" else f"{value:.3f}" if key == "URL_Entropy" else str(int(value)))
        st.dataframe(result[0].T.rename(columns={result[0].index[0]: "Value"}).astype(str), use_container_width=True)
    st.caption("Never rely on this prediction alone to decide whether to enter credentials or financial information.")

with performance:
    st.subheader("Held-out test results")
    metrics_file = ROOT / "model_comparison.csv"
    if metrics_file.exists():
        metrics = pd.read_csv(metrics_file, index_col=0)
        st.dataframe(metrics.style.format(precision=4), use_container_width=True)
        available = [name for name in ["Accuracy", "Precision", "Recall", "F1-score", "ROC-AUC"] if name in metrics]
        if available:
            metric = st.selectbox("Compare models by", available, index=available.index("F1-score") if "F1-score" in available else 0)
            st.bar_chart(metrics[[metric]])
    else:
        st.info("Add model_comparison.csv from your training notebook to display the actual test metrics here.")
    st.caption("No estimated or fabricated evaluation scores are displayed.")

with about:
    st.subheader("From raw data to classification")
    st.markdown("**01 — Data source** · UCI PhiUSIIL Phishing URL Dataset (2024)\n\n**02 — Preparation** · Cleaning, duplicate checks, group-based holdout and preprocessing\n\n**03 — Feature engineering** · Ten reproducible URL features and information gain analysis\n\n**04 — Modeling** · Decision Tree, Gaussian Naive Bayes and Linear SVM\n\n**05 — Evaluation** · Accuracy, Precision, Recall, F1-score, ROC-AUC and confusion matrices")
    st.markdown("[Original UCI dataset](https://archive.ics.uci.edu/dataset/967/phiusiil+phishing+url+dataset)")
    st.warning("Limitations: URL text alone cannot verify a website's identity, page content, certificate validity or current reputation. Predictions can be wrong.")

st.markdown('<div class="pg-footer">PHISHGUARD <span> / DATA MINING TERM PROJECT · EDUCATIONAL PROTOTYPE</span></div>', unsafe_allow_html=True)
