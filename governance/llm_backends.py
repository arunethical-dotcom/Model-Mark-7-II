"""
LLM Backends for Cognitive Governance.
"""

import json
import requests
from abc import ABC, abstractmethod

class LLMBackend(ABC):
    @abstractmethod
    def __call__(self, messages: list[dict]) -> str:
        ...

class OllamaBackend(LLMBackend):
    def __init__(self, model: str, host: str = "http://localhost:11434", timeout: int = 30):
        self.model = model
        self.host = host.rstrip("/")
        self.timeout = timeout

    def _messages_to_prompt(self, messages: list[dict]) -> str:
        prompt = ""
        for msg in messages:
            role = msg.get("role")
            content = msg.get("content", "")
            if role == "system":
                prompt += f"{content}\n\n"
            elif role == "user":
                prompt += f"User: {content}\n"
        prompt += "Assistant: "
        return prompt

    def __call__(self, messages: list[dict], *, stream: bool = True, **kwargs) -> str:
        temperature = kwargs.get('temperature', 0.2)
        max_tokens = kwargs.get('num_predict', 120)
        stop = kwargs.get('stop', None)
        
        # Support model override per call
        model = kwargs.get('model', self.model)
        
        # Use /api/chat for better template handling
        payload = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                "stop": stop
            }
        }
        
        # DEBUG
        print(f"[DEBUG] OLLAMA Request: {self.host}/api/chat")
        print(f"[DEBUG] Payload model: '{model}'")

        try:
            url = f"{self.host}/api/chat"
            if stream:
                response_text = ""
                with requests.post(url, json=payload, stream=True, timeout=self.timeout) as r:
                    if r.status_code != 200:
                         print(f"[OLLAMA] HTTP Error {r.status_code}: {r.text}")
                         r.raise_for_status()
                    
                    buffer = ""
                    for chunk in r.iter_content(chunk_size=None):
                        if not chunk: continue
                        
                        try:
                            text_chunk = chunk.decode("utf-8")
                            buffer += text_chunk
                            
                            while "\n" in buffer:
                                line, buffer = buffer.split("\n", 1)
                                if not line.strip(): continue
                                
                                try:
                                    data = json.loads(line)
                                except json.JSONDecodeError:
                                    continue
                                    
                                if data.get("done"): break
                                
                                # Parse chat response structure
                                # {"model":..., "message":{"role":"assistant", "content":"..."}, "done":false}
                                token = data.get("message", {}).get("content", "")
                                response_text += token
                        except Exception:
                            continue
                            
                return response_text.strip()
            else:
                response = requests.post(url, json=payload, timeout=self.timeout)
                if response.status_code != 200:
                     print(f"[OLLAMA] HTTP Error {response.status_code}: {response.text}")
                     response.raise_for_status()
                result = response.json()
                return result.get("message", {}).get("content", "").strip()

        except Exception as e:
            print(f"[OLLAMA] Error: {e}")
            raise

    def health_check(self) -> bool:
        try:
            r = requests.get(f"{self.host}/api/tags", timeout=2)
            return r.status_code == 200
        except Exception:
            return False

class MockBackend:
    def __init__(self, response: str = "As JARVIIS, I'm here to help."):
        self.response = response
    def __call__(self, messages: list, **kwargs) -> str:
        return self.response
    def health_check(self) -> bool:
        return True
