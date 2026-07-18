"""
Project persistence helpers — saves/loads project JSON files in ./projects/ folder
"""
import json, os, glob
from datetime import datetime

PROJECTS_DIR = os.path.join(os.path.dirname(__file__), "projects")
os.makedirs(PROJECTS_DIR, exist_ok=True)

def list_projects():
    files = glob.glob(os.path.join(PROJECTS_DIR, "*.json"))
    projects = []
    for f in sorted(files, key=os.path.getmtime, reverse=True):
        try:
            with open(f) as fp:
                d = json.load(fp)
            projects.append({
                "name": d.get("project_name", os.path.basename(f)),
                "file": f,
                "modified": datetime.fromtimestamp(os.path.getmtime(f)).strftime("%d %b %Y %H:%M"),
                "n_units": d.get("n_units", 1),
                "scheme": d.get("units", [{}])[0].get("scheme", "—") if d.get("units") else "—",
            })
        except Exception:
            pass
    return projects

def save_project(data: dict):
    name = data.get("project_name", "untitled").replace(" ", "_").replace("/","_")
    path = os.path.join(PROJECTS_DIR, f"{name}.json")
    data["saved_at"] = datetime.now().isoformat()
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    return path

def load_project(path: str) -> dict:
    with open(path) as f:
        return json.load(f)

def delete_project(path: str):
    if os.path.exists(path):
        os.remove(path)
