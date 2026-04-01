import os
import json
import re

class InstructionManager:
    """Manages global instructions with in-memory caching to avoid blocking I/O."""
    
    def __init__(self, directory="instructions", state_file="instructions_state.json"):
        self.directory = directory
        self.state_file = os.path.join(directory, state_file)
        self._cache = {} # {name: content}
        self.active_instructions = []
        
        if not os.path.exists(self.directory):
            os.makedirs(self.directory)
            
        self.refresh_cache()
        self.active_instructions = self._load_state()

    def refresh_cache(self):
        """Synchronously refreshes the in-memory cache of instruction files."""
        if not os.path.exists(self.directory):
            return
        
        new_cache = {}
        for f in os.listdir(self.directory):
            if f.endswith(".txt"):
                name = f[:-4]
                path = os.path.join(self.directory, f)
                try:
                    with open(path, "r", encoding="utf-8") as file:
                        new_cache[name] = file.read().strip()
                except: continue
        self._cache = new_cache

    def _load_state(self):
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r") as f:
                    return json.load(f)
            except:
                return []
        return []

    def _save_state(self):
        with open(self.state_file, "w") as f:
            json.dump(self.active_instructions, f)

    def sanitize_name(self, name):
        return re.sub(r'[^\w\s-]', '', name).strip()

    def get_path(self, name):
        sanitized = self.sanitize_name(name)
        return os.path.join(self.directory, f"{sanitized}.txt")

    def create_or_update(self, name, content):
        sanitized = self.sanitize_name(name)
        path = self.get_path(sanitized)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        self._cache[sanitized] = content

    def delete(self, name):
        sanitized = self.sanitize_name(name)
        path = self.get_path(sanitized)
        if os.path.exists(path):
            os.remove(path)
            if sanitized in self._cache:
                del self._cache[sanitized]
            if sanitized in self.active_instructions:
                self.active_instructions.remove(sanitized)
                self._save_state()
            return True
        return False

    def toggle(self, name, status: bool):
        sanitized = self.sanitize_name(name)
        if sanitized not in self._cache:
            return False
        
        if status and sanitized not in self.active_instructions:
            self.active_instructions.append(sanitized)
        elif not status and sanitized in self.active_instructions:
            self.active_instructions.remove(sanitized)
        
        self._save_state()
        return True

    def list_all(self):
        """Returns sorted names and active status from cache (instant)."""
        names = sorted(list(self._cache.keys()))
        return [(name, name in self.active_instructions) for name in names]

    def get_active_content(self):
        """Returns concatenated content from cache (instant)."""
        content_list = []
        for name in self.active_instructions:
            if name in self._cache:
                content_list.append(self._cache[name])
        return "\n".join(content_list)
