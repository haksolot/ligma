import os
import re

class PersonalityManager:
    """Manages bot personalities with in-memory caching to avoid blocking I/O."""
    
    def __init__(self, directory="personalities", default_name="default"):
        self.directory = directory
        self.default_name = default_name
        self.current_name = default_name
        self._cache = {} # {name: content}
        
        if not os.path.exists(self.directory):
            os.makedirs(self.directory)
            # Create a default if it doesn't exist
            self.save("default", "You are a helpful and professional AI assistant.")

        # Initial load
        self.refresh_cache()
        self.current_personality = self.load(self.current_name)

    def sanitize_name(self, name):
        return re.sub(r'[^\w\s-]', '', name).strip()

    def refresh_cache(self):
        """Synchronously refreshes the in-memory cache from disk."""
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

    def get_path(self, name):
        sanitized = self.sanitize_name(name)
        return os.path.join(self.directory, f"{sanitized}.txt")

    def load(self, name):
        """Retrieves a personality from cache or fallback to disk/default."""
        sanitized = self.sanitize_name(name)
        if sanitized in self._cache:
            self.current_name = sanitized
            self.current_personality = self._cache[sanitized]
            return self.current_personality
        
        # Fallback to disk if cache missed (safety)
        path = self.get_path(sanitized)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                self._cache[sanitized] = content
                self.current_name = sanitized
                self.current_personality = content
                return content
        
        # Absolute fallback to default
        self.current_name = "default"
        self.current_personality = self._cache.get("default", "Helpful assistant.")
        return self.current_personality

    def save(self, name, content):
        """Saves a personality to disk and updates cache."""
        sanitized = self.sanitize_name(name)
        path = self.get_path(sanitized)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        
        self._cache[sanitized] = content
        if sanitized == self.current_name:
            self.current_personality = content

    def delete(self, name):
        sanitized = self.sanitize_name(name)
        if sanitized == "default":
            return False
            
        path = self.get_path(sanitized)
        if os.path.exists(path):
            os.remove(path)
            if sanitized in self._cache:
                del self._cache[sanitized]
            if self.current_name == sanitized:
                self.load("default")
            return True
        return False

    def list_all(self):
        """Returns all available names from cache (instant)."""
        return sorted(list(self._cache.keys()))
