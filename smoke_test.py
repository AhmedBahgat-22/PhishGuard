"""Verify model inference; optionally remove legacy serialized functions safely."""
from pathlib import Path
import sys
import shutil
from importlib.metadata import version
import numpy as np
import pandas as pd
from features import feature_frame
from model_io import load_bundle, save_bundle

ROOT = Path(__file__).resolve().parent
print("Python:", sys.version.split()[0])
for package in ("numpy", "pandas", "scipy", "scikit-learn", "cloudpickle", "streamlit"):
    print(f"{package}: {version(package)}")
assert version("scikit-learn") == "1.6.1", "Use the original model's scikit-learn version."
path = ROOT / "models.pkl"
models, columns = load_bundle(path)
urls = ["https://example.com", "https://example.org/a/b?q=42", "http://example.net/"]
data = pd.concat([feature_frame(url, columns) for url in urls], ignore_index=True)
predictions = {}
for name, model in models.items():
    assert set(model.classes_) == {0, 1}
    values = model.predict(data)
    assert set(values).issubset({0, 1})
    predictions[name] = values
    print(f"{name}: {'Phishing' if values[0] else 'Legitimate'}")
metrics = pd.read_csv(ROOT / "model_comparison.csv", index_col=0)
assert set(metrics.index) == set(models)
assert set(metrics.columns) == {"Accuracy", "Precision", "Recall", "F1-score", "ROC-AUC"}
if "--migrate" in sys.argv:
    temp = ROOT / "models.pkl.tmp"
    backup = ROOT / "models.pkl.bak"
    try:
        save_bundle(temp, models, columns)
        restored, restored_columns = load_bundle(temp)
        assert restored_columns == columns
        for name, model in restored.items():
            np.testing.assert_array_equal(model.predict(data), predictions[name])
            original = models[name]
            if hasattr(original, "predict_proba"):
                np.testing.assert_allclose(model.predict_proba(data), original.predict_proba(data))
            if hasattr(original, "decision_function"):
                np.testing.assert_allclose(model.decision_function(data), original.decision_function(data))
        if not backup.exists():
            shutil.copy2(path, backup)
        temp.replace(path)
        print("MIGRATED: model-only bundle saved; original backed up.")
    finally:
        temp.unlink(missing_ok=True)
print("PASS: all three models loaded and predicted successfully.")
