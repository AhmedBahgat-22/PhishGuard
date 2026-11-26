"""URL feature extraction, unchanged from the training notebook."""
from collections import Counter
from urllib.parse import urlsplit
import numpy as np
import pandas as pd

def extract_features(url):
    parsed = urlsplit(url)
    length = max(len(url), 1)
    probabilities = np.array(list(Counter(url).values())) / length

    return {
        "URL_Entropy": -np.sum(probabilities * np.log2(probabilities)),
        "Digit_Ratio": sum(c.isdigit() for c in url) / length,
        "Special_Ratio": sum(not c.isalnum() for c in url) / length,
        "Path_Depth": len([p for p in parsed.path.split("/") if p]),
        "Query_Count": len(parsed.query.split("&")) if parsed.query else 0,
        "Path_Length": len(parsed.path)
    }

def basic_features(url):
    parsed = urlsplit(url)
    host = parsed.hostname or ""
    suffix = host.rsplit(".", 1)[-1] if "." in host else "unknown"

    return {
        "URL_Length": len(url),
        "Host_Length": len(host),
        "HTTPS": int(parsed.scheme.lower() == "https"),
        "Host_Suffix": suffix if suffix.isalpha() else "unknown"
    }

def feature_frame(url, columns):
    return pd.DataFrame([{**extract_features(url), **basic_features(url)}])[columns]
