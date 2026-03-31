import os
import json
import re

class InstructionManager:
    """Manages global instructions that can be toggled on/off."""
    
    def __init__(self, directory="instructions", state_file="instructions_state.json"):
        self.directory = directory
        self.state_file = os.path.join(directory, state_file)
        
        if not os.path.exists(self.directory):
            os.makedirs(self.directory)
            
        self.active_instructions = self._load_state()

    def _load_state(self):
        """Loads the list of active instruction names from a JSON file."""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r") as f:
                    return json.load(f)
            except:
                return []
        return []

    def _save_state(self):
        """Saves the list of active instruction names to a JSON file."""
        with open(self.state_file, "w") as f:
            json.dump(self.active_instructions, f)

    def sanitize_name(self, name):
        return re.sub(r'[^\w\s-]', '', name).strip()

    def get_path(self, name):
        sanitized = self.sanitize_name(name)
        return os.path.join(self.directory, f"{sanitized}.txt")

    def create_or_update(self, name, content):
        path = self.get_path(name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    def delete(self, name):
        sanitized = self.sanitize_name(name)
        path = self.get_path(sanitized)
        if os.path.exists(path):
            os.remove(path)
            if sanitized in self.active_instructions:
                self.active_instructions.remove(sanitized)
                self._save_state()
            return True
        return False

    def toggle(self, name, status: bool):
        sanitized = self.sanitize_name(name)
        if not os.path.exists(self.get_path(sanitized)):
            return False
        
        if status and sanitized not in self.active_instructions:
            self.active_instructions.append(sanitized)
        elif not status and sanitized in self.active_instructions:
            self.active_instructions.remove(sanitized)
        
        self._save_state()
        return True

    def list_all(self):
        """Returns a list of tuples (name, is_active)."""
        files = [f for f in os.listdir(self.directory) if f.endswith(".txt")]
        names = [f[:-4] for f in files]
        return [(name, name in self.active_instructions) for name in names]

    def get_active_content(self):
        """Returns a concatenated string of all active instructions."""
        content_list = []
        for name in self.active_instructions:
            path = self.get_path(name)
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    content_list.append(f.read().strip())
        return "\n".join(content_list)
