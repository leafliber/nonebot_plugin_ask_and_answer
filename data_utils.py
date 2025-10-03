import json
import os
from typing import List, Optional

DATA_DIR = "data/nonebot_plugin_ask_and_answer"
META_PATH = os.path.join(DATA_DIR, "meta.json")

def ensure_data_dir():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

def get_question_bank_path(bank_name: str) -> str:
    return os.path.join(DATA_DIR, f"{bank_name}.json")

def load_meta():
    if not os.path.exists(META_PATH):
        with open(META_PATH, "w", encoding="utf-8") as f:
            json.dump({"current_bank": "default"}, f)
    with open(META_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_meta(meta):
    with open(META_PATH, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

def load_bank(bank_name: str):
    path = get_question_bank_path(bank_name)
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"questions": [], "current_question": None}, f, ensure_ascii=False, indent=2)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_bank(bank_name: str, data):
    path = get_question_bank_path(bank_name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def list_banks() -> List[str]:
    ensure_data_dir()
    return [f[:-5] for f in os.listdir(DATA_DIR) if f.endswith('.json') and f != 'meta.json']
