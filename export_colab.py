# Run only after Sections 8–11 have completed successfully.
import sys
import json
import zipfile
import pickle
from importlib.metadata import version
from pathlib import Path

required = ("trained_models", "extract_features", "basic_features", "selected_columns", "results_df")
missing = [name for name in required if name not in globals()]
if missing:
    raise RuntimeError("Run the training and evaluation cells first. Missing: " + ", ".join(missing))

with open("models.pkl", "wb") as f:
    pickle.dump({"format": "phishguard-models-v1", "models": trained_models, "columns": list(selected_columns)}, f, protocol=4)
results_df.to_csv("model_comparison.csv")

# Match the runtime used to serialize the scikit-learn pipelines.
packages = ["numpy", "pandas", "scipy", "scikit-learn", "cloudpickle", "joblib", "threadpoolctl"]
versions = {name: version(name) for name in packages}
requirements = "streamlit==1.51.0\n" + "\n".join(f"{name}=={v}" for name, v in versions.items()) + "\n"
Path("requirements.txt").write_text(requirements, encoding="utf-8")
python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
Path("model_environment.json").write_text(json.dumps({"python": python_version, "packages": versions}, indent=2), encoding="utf-8")

# Verify the exported bundle in the same runtime with a harmless example.
with open("models.pkl", "rb") as f:
    bundle = pickle.load(f)
    saved_models, columns = bundle["models"], bundle["columns"]
example = "https://example.com"
features = pd.DataFrame([{**extract_features(example), **basic_features(example)}])[columns]
assert all(int(m.predict(features)[0]) == int(trained_models[name].predict(features)[0]) for name, m in saved_models.items())

with zipfile.ZipFile("PhishGuard_Deployment_Files.zip", "w", zipfile.ZIP_DEFLATED) as z:
    for name in ["models.pkl", "model_comparison.csv", "requirements.txt", "model_environment.json"]:
        z.write(name)
print("Export verified. Deployment Python version:", python_version)
from google.colab import files
files.download("PhishGuard_Deployment_Files.zip")
