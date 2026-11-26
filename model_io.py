"""Read trusted legacy or model-only bundles. Never load untrusted pickle files."""
import pickle
from importlib.metadata import version


def load_bundle(path):
    with path.open("rb") as f:
        bundle = pickle.load(f)
    if isinstance(bundle, dict) and bundle.get("format") == "phishguard-models-v1":
        models, columns = bundle["models"], bundle["columns"]
    elif isinstance(bundle, tuple) and len(bundle) == 4:
        # Ignore serialized notebook functions: use features.py instead.
        models, _, _, columns = bundle
    else:
        raise ValueError("Unknown model bundle format")
    if set(models) != {"Decision Tree", "Naive Bayes", "SVM"} or len(columns) != 10:
        raise ValueError("Unexpected model names or feature count")
    return models, list(columns)


def save_bundle(path, models, columns):
    with path.open("wb") as f:
        pickle.dump({"format": "phishguard-models-v1", "models": models,
                     "columns": list(columns)}, f, protocol=4)
