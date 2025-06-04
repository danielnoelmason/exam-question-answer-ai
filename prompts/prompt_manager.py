import json
import os

class PromptManager:
    def __init__(self, file_path=None):
        default_path = os.path.join(os.path.dirname(__file__), "templates.json")
        self.file_path = file_path or default_path
        self.prompts = self._load()

    def _load(self):
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"Prompt file not found: {self.file_path}")
        with open(self.file_path, "r") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                raise ValueError("Prompt file must be a JSON object of named templates.")
            for name, obj in data.items():
                if "template" not in obj:
                    raise ValueError(f"Prompt '{name}' is missing a 'template' field.")
            return data

    def get(self, name):
        if name not in self.prompts:
            raise KeyError(f"Prompt '{name}' not found.")
        return self.prompts[name]["template"]

    def describe(self, name):
        return self.prompts.get(name, {}).get("description", "No description available.")

    def list(self):
        return [(name, self.describe(name)) for name in self.prompts]
