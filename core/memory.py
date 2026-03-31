import ollama

class MemoryManager:
    def __init__(self, limit=10):
        self.history = {}  # {channel_id: [messages]}
        self.summaries = {}  # {channel_id: "summary"}
        self.limit = limit
        self.client = ollama.AsyncClient()

    async def add_message(self, channel_id, role, content):
        if channel_id not in self.history:
            self.history[channel_id] = []
        
        self.history[channel_id].append({'role': role, 'content': content})
        
        # Compress if too many messages
        if len(self.history[channel_id]) > self.limit:
            await self.compress(channel_id)

    async def get_context(self, channel_id, personality, user_message):
        messages = []
        
        # Add summary if it exists
        if channel_id in self.summaries:
            messages.append({'role': 'system', 'content': f"Context summary: {self.summaries[channel_id]}"})
        
        # Add recent history
        if channel_id in self.history:
            messages.extend(self.history[channel_id])
            
        # Add the current System Prompt (Personality + Instructions) 
        # just before the new user message to give it maximum weight.
        messages.append({'role': 'system', 'content': personality})
        
        messages.append({'role': 'user', 'content': user_message})
        return messages

    async def compress(self, channel_id):
        """Compresses old messages to avoid overloading memory."""
        try:
            old_summary = self.summaries.get(channel_id, "")
            messages_to_compress = self.history[channel_id][:-2]  # Keep the last 2
            
            prompt = f"""
            Here is the previous context: {old_summary}
            Here are new exchanges: {messages_to_compress}
            Instruction: Make an extremely concise summary (max 2 sentences) of this information.
            """
            
            response = await self.client.chat(model="llama3.2:1b", messages=[
                {'role': 'system', 'content': 'You are an expert in raw text synthesis.'},
                {'role': 'user', 'content': prompt}
            ])
            
            self.summaries[channel_id] = response['message']['content']
            self.history[channel_id] = self.history[channel_id][-2:]  # Cleanup
            print(f"[Memory] Compression completed for {channel_id}.")
            
        except Exception as e:
            print(f"[Memory] Compression error: {e}")

    def clear(self, channel_id):
        if channel_id in self.history:
            self.history[channel_id] = []
        if channel_id in self.summaries:
            del self.summaries[channel_id]
