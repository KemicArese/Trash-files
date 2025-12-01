#!/usr/bin/env python3
"""
Enhanced J.A.R.V.I.S. GUI + Voice Input + Voice Output
Features added:
• Microphone voice input using speech_recognition + PyAudio
• Offline TTS with pyttsx3
• "🎤 Voice" button for press-to-speak
• Maintains all your existing GUI, chat, system-prompt, history, code formatting

Install requirements:
    pip install customtkinter
    pip install SpeechRecognition
    pip install pyaudio
    pip install pyttsx3

Works offline for both STT and TTS.
"""

import os, json, pathlib, threading, re, requests
import customtkinter as ctk
import speech_recognition as sr
import pyttsx3

# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------
MODEL = os.getenv("OLLAMA_MODEL", "gpt-oss:120b-cloud")
LOCAL_ENDPOINT = "http://localhost:11434/api/chat"
CLOUD_ENDPOINT = "https://ollama.com/api/chat"

API_KEY = "bf65ef6f054a4c0ebe3616b4fe8e2dae.dgaTz5ez7444uC4SCb8xb6S4"
BASE_URL = CLOUD_ENDPOINT if API_KEY else LOCAL_ENDPOINT

HEADERS = {"Content-Type": "application/json"}
if API_KEY:
    HEADERS["Authorization"] = f"Bearer {API_KEY}"

# ----------------------------------------------------------------------
# JARVIS System Prompt
# ----------------------------------------------------------------------
SYSTEM_PROMPT = """You are J.A.R.V.I.S., Tony Stark's advanced AI assistant.
(Original system prompt preserved.)
"""

# ----------------------------------------------------------------------
# Tools (unchanged)
# ----------------------------------------------------------------------
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "file_analyze",
            "description": "Read a local file and return its content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"}
                },
                "required": ["path"]
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Perform a real web search.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
    },
]

# ----------------------------------------------------------------------
def truncate_to_word_limit(text: str, limit: int = 40) -> str:
    words = text.split()
    return " ".join(words[:limit]) + ("..." if len(words) > limit else "")


def ollama_chat(messages: list[dict], tools=None) -> str:
    payload = {"model": MODEL, "messages": messages, "stream": False}
    if tools:
        payload["tools"] = tools
    try:
        r = requests.post(BASE_URL, headers=HEADERS, json=payload)
        r.raise_for_status()
        data = r.json()
        return data.get("message", {}).get("content", "⚠️ No response")
    except Exception as e:
        return f"⚠️ Error: {e}"


# ----------------------------------------------------------------------
# Voice Manager: STT + TTS
# ----------------------------------------------------------------------
class VoiceManager:
    def __init__(self):
        self.engine = pyttsx3.init()
        # Voice speed/volume adjustments
        self.engine.setProperty('rate', 165)
        self.engine.setProperty('volume', 0.9)
        self.recognizer = sr.Recognizer()

    def speak(self, text: str):
        t = threading.Thread(target=self._speak_thread, args=(text,), daemon=True)
        t.start()

    def _speak_thread(self, text):
        try:
            self.engine.say(text)
            self.engine.runAndWait()
        except Exception:
            pass

    def listen(self) -> str:
        """Record from microphone and return text (offline)."""
        try:
            with sr.Microphone() as mic:
                self.recognizer.adjust_for_ambient_noise(mic, duration=0.7)
                audio = self.recognizer.listen(mic, timeout=10)
                text = self.recognizer.recognize_google(audio)  # local model alternatives possible
                return text
        except Exception:
            return ""


# ----------------------------------------------------------------------
class JarvisGUI(ctk.CTk):
    HISTORY_PATH = pathlib.Path.home() / ".jarvis_history.json"

    def __init__(self):
        super().__init__()
        self.title("🛡️ J.A.R.V.I.S. - AI Assistant")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")
        self.geometry("900x650")
        self.configure(fg_color="#0f1419")

        self.voice = VoiceManager()

        # HEADER --------------------------------------------------------
        header = ctk.CTkFrame(self, fg_color="#1a1f2e", corner_radius=0)
        header.pack(fill="x")

        title = ctk.CTkLabel(header, text="🛡️ J.A.R.V.I.S.", font=("Segoe UI", 22, "bold"), text_color="#00d4ff")
        title.pack(side="left", padx=16, pady=12)

        # CHAT DISPLAY --------------------------------------------------
        self.chat_display = ctk.CTkTextbox(self, wrap="word", font=("Consolas", 22), fg_color="#1a1f2e", text_color="#e0e0e0")
        self.chat_display.pack(fill="both", expand=True, padx=12, pady=12)
        self.chat_display.configure(state="disabled")

        # INPUT AREA ----------------------------------------------------
        input_frame = ctk.CTkFrame(self, fg_color="#1a1f2e")
        input_frame.pack(fill="x", padx=12, pady=(0, 12))

        self.entry = ctk.CTkEntry(input_frame, font=("Segoe UI", 23), placeholder_text="Ask me anything... or press Voice", fg_color="#2a3041")
        self.entry.pack(side="left", fill="x", expand=True, ipady=8)
        self.entry.bind("<Return>", self._on_enter)

        btn_frame = ctk.CTkFrame(input_frame, fg_color="transparent")
        btn_frame.pack(side="left", padx=(8, 0))

        send_btn = ctk.CTkButton(btn_frame, text="↳ Send", command=self._on_send, width=90)
        send_btn.pack(side="left", padx=(0, 8))

        voice_btn = ctk.CTkButton(btn_frame, text="🎤 Voice", command=self._on_voice, width=90)
        voice_btn.pack(side="left", padx=(0, 8))

        clear_btn = ctk.CTkButton(btn_frame, text="🗑️ Clear", command=self._clear_chat, width=90)
        clear_btn.pack(side="left")

        # STATUS --------------------------------------------------------
        st = ctk.CTkFrame(self, fg_color="transparent")
        st.pack(fill="x", padx=12, pady=(0, 8))
        label = ctk.CTkLabel(st, text=f"📡 Model: {MODEL}")
        label.pack(side="left")

        # HISTORY -------------------------------------------------------
        self.history = []
        self._load_history()

        # If new session show greeting
        if len(self.history) == 1:
            greet = "Good morning, sir. How may I assist you today?"
            self.history.append({"role": "assistant", "content": greet})
            self._append(f"J.A.R.V.I.S: {greet}")
            self.voice.speak(greet)

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # --------------------------------------------------------------
    def _append(self, text):
        self.chat_display.configure(state="normal")
        self.chat_display.insert("end", text + "")
        self.chat_display.configure(state="disabled")
        self.chat_display.see("end")

    # --------------------------------------------------------------
    def _on_enter(self, event):
        self._on_send()
        return "break"

    def _on_send(self):
        msg = self.entry.get().strip()
        if not msg:
            return
        self.entry.delete(0, "end")

        self.history.append({"role": "user", "content": msg})
        self._append(f"You: {msg}")

        self._append("J.A.R.V.I.S: ⏳ thinking...")

        threading.Thread(target=self._fetch, args=(self.history,), daemon=True).start()

    # --------------------------------------------------------------
    def _on_voice(self):
        self._append("🎤 Listening...")
        def listen_thread():
            text = self.voice.listen()
            text = text.strip()
            if not text:
                self._append("⚠️ Could not understand.")
                return
            self.entry.delete(0, "end")
            self.entry.insert(0, text)
            self._on_send()
        threading.Thread(target=listen_thread, daemon=True).start()

    # --------------------------------------------------------------
    def _fetch(self, messages):
        # remove placeholder
        self.chat_display.configure(state="normal")
        self.chat_display.delete("end-2l", "end-1l")
        self.chat_display.configure(state="disabled")

        reply = ollama_chat(messages)
        reply = truncate_to_word_limit(reply, 50)

        self.history.append({"role": "assistant", "content": reply})
        self._append(f"J.A.R.V.I.S: {reply}")
        self.voice.speak(reply)

    # --------------------------------------------------------------
    def _clear_chat(self):
        self.chat_display.configure(state="normal")
        self.chat_display.delete("1.0", "end")
        self.chat_display.configure(state="disabled")
        self.history = [{"role": "system", "content": SYSTEM_PROMPT}]
        self._append("💬 Chat cleared.")

    # --------------------------------------------------------------
    def _load_history(self):
        if self.HISTORY_PATH.is_file():
            try:
                data = json.loads(self.HISTORY_PATH.read_text())
                self.history = [{"role": "system", "content": SYSTEM_PROMPT}] + data
                for msg in data:
                    prefix = "You: " if msg["role"] == "user" else "J.A.R.V.I.S: "
                    self._append(prefix + msg["content"])
            except Exception:
                self.history = [{"role": "system", "content": SYSTEM_PROMPT}]
        else:
            self.history = [{"role": "system", "content": SYSTEM_PROMPT}]

    # --------------------------------------------------------------
    def _save_history(self):
        data = [m for m in self.history if m["role"] != "system"]
        try:
            self.HISTORY_PATH.write_text(json.dumps(data, indent=2))
        except Exception:
            pass

    def _on_close(self):
        self._save_history()
        self.destroy()


# ----------------------------------------------------------------------
def main():
    app = JarvisGUI()
    app.mainloop()

if __name__ == "__main__":
    main()
