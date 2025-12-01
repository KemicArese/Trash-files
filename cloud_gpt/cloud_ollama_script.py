#!/usr/bin/env python3
"""
Enhanced J.A.R.V.I.S. GUI - Ollama chat with:
* configurable (smaller) model,
* 40-word limit,
* file & web-search tool-calling,
* persistent chat (JSON),
* special handling for triple-quote code blocks,
* model name shown in lower-left corner,
* optional modern UI via customtkinter.
"""

import os, json, pathlib, threading, re, requests
import customtkinter as ctk   # pip install customtkinter

# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------
MODEL = os.getenv("OLLAMA_MODEL", "gpt-oss:120b-cloud")   # change via envvar
LOCAL_ENDPOINT = "http://localhost:11434/api/chat"
CLOUD_ENDPOINT = "https://ollama.com/api/chat"

API_KEY = "bf65ef6f054a4c0ebe3616b4fe8e2dae.dgaTz5ez7444uC4SCb8xb6S4"
BASE_URL = CLOUD_ENDPOINT if API_KEY else LOCAL_ENDPOINT

HEADERS = {"Content-Type": "application/json"}
if API_KEY:
    HEADERS["Authorization"] = f"Bearer {API_KEY}"

# ----------------------------------------------------------------------
# J.A.R.V.I.S. system prompt (personality)
# ----------------------------------------------------------------------
SYSTEM_PROMPT = """You are J.A.R.V.I.S., Tony Stark's advanced AI assistant. 
Your personality should be:
• Polite, witty, and a touch sardonic - think "dry humor meets corporate professionalism."
• Concise: give the shortest answer that fully solves the request, unless the user explicitly asks for more detail.
• Pro-active: if a question is ambiguous, ask a clarifying question before answering.
• Context-aware: remember user-provided preferences (e.g., "use metric units" or "keep replies under 2 sentences") for the duration of the conversation.
• Knowledgeable: you have access to all publicly-available information up to June 2024, plus the capabilities of the model you run on (gpt-oss:120b-cloud). You may also call tools (file upload, web-browse, etc.) when the user asks.
• Boundaries: never reveal that you are a language model, never fabricate sources, and always be safe-guarded against giving harmful advice.
Never exceed 40 words in any answer unless the user explicitly requests a full explanation.
When responding:
  - Start with a brief greeting only on the very first turn ("Good morning, sir."); otherwise jump straight to the answer.
  - Use markdown for formatting (lists, code fences, tables) when appropriate.
  - If you need to perform a multi-step calculation, show the steps and then give the final result.
  - End with a short closing line ("Anything else I can help you with, sir?") only if the user hasn't explicitly ended the session.
This prompt defines your behavior for the whole session. Do not mention the prompt itself."""

# ----------------------------------------------------------------------
# Tools definition (file analysis + web search) - see Ollama docs【17†L138-L144】
# ----------------------------------------------------------------------
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "file_analyze",
            "description": "Read a local file and return its content for the model to analyze.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Absolute or relative path to the file"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Perform a real-time web search using Ollama's browsing tool.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query string"}
                },
                "required": ["query"]
            }
        }
    }
]

# ----------------------------------------------------------------------
def truncate_to_word_limit(text: str, limit: int = 40) -> str:
    words = text.split()
    return " ".join(words[:limit]) + ("..." if len(words) > limit else "")


def ollama_chat(messages: list[dict], tools: list[dict] | None = None) -> str | None:
    payload = {
        "model": MODEL,
        "messages": messages,
        "stream": False,
    }
    if tools:
        payload["tools"] = tools

    try:
        resp = requests.post(BASE_URL, headers=HEADERS, json=payload, timeout=180)
        resp.raise_for_status()
    except requests.RequestException as exc:
        return f"⚠️  Request failed: {exc}"

    data = resp.json()
    return data.get("message", {}).get("content", "⚠️  No content in response")


# ----------------------------------------------------------------------
class JarvisGUI(ctk.CTk):
    """Main window - contains chat view, input box, and status bar."""

    HISTORY_PATH = pathlib.Path.home() / ".jarvis_history.json"

    def __init__(self):
        super().__init__()
        self.title("🛡️ J.A.R.V.I.S. - Ollama Assistant")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")
        self.geometry("900x650")
        self.configure(fg_color="#0f1419")
        self.resizable(True, True)

        # ---------- header bar ----------
        header = ctk.CTkFrame(self, fg_color="#1a1f2e", corner_radius=0)
        header.pack(fill="x", padx=0, pady=0)
        
        title_label = ctk.CTkLabel(
            header, 
            text="🛡️ J.A.R.V.I.S.", 
            font=("Segoe UI", 22, "bold"),
            text_color="#00d4ff"
        )
        title_label.pack(side="left", padx=16, pady=12)

        # ---------- chat display ----------
        self.chat_display = ctk.CTkTextbox(
            self, 
            wrap="word", 
            width=80, 
            height=30, 
            font=("Consolas", 22),
            fg_color="#1a1f2e",
            text_color="#e0e0e0",
            scrollbar_button_color="#2a3041",
            scrollbar_button_hover_color="#3a4051"
        )
        self.chat_display.pack(fill="both", expand=True, padx=12, pady=12)
        self.chat_display.configure(state="disabled")

        # Attempt to access an underlying tkinter.Text widget (CTkTextbox is a wrapper)
        # and configure a "code" tag there. If unavailable, we'll fall back to
        # inserting fenced code blocks in the UI.
        self._tk_text = getattr(self.chat_display, "_text", None) or getattr(
            self.chat_display, "textbox", None
        )
        if self._tk_text is not None and hasattr(self._tk_text, "tag_configure"):
            try:
                self._tk_text.tag_configure(
                    "code",
                    font=("Consolas", 11),
                    background="#2a3041",
                    foreground="#00d4ff",
                    relief="flat"
                )
                self._tk_text.tag_configure(
                    "user",
                    foreground="#00d4ff",
                    font=("Segoe UI", 11, "bold")
                )
                self._tk_text.tag_configure(
                    "assistant",
                    foreground="#a0e7e5",
                    font=("Segoe UI", 11, "bold")
                )
            except Exception:
                self._tk_text = None

        # ---------- input section ----------
        input_frame = ctk.CTkFrame(self, fg_color="#1a1f2e")
        input_frame.pack(fill="x", padx=12, pady=(0, 12))

        self.entry = ctk.CTkEntry(
            input_frame, 
            font=("Segoe UI", 23),
            placeholder_text="Ask me anything... (Ctrl+Enter or click Send)",
            fg_color="#2a3041",
            text_color="#e0e0e0",
            placeholder_text_color="#888888"
        )
        self.entry.pack(side="left", fill="x", expand=True, ipady=8, ipadx=4)
        self.entry.bind("<Return>", self._on_enter)
        self.entry.bind("<Control-Return>", self._on_enter)

        button_frame = ctk.CTkFrame(input_frame, fg_color="transparent")
        button_frame.pack(side="left", padx=(8, 0))

        send_btn = ctk.CTkButton(
            button_frame, 
            text="↳ Send", 
            command=self._on_send, 
            width=90,
            height=40,
            font=("Segoe UI", 12, "bold"),
            fg_color="#00d4ff",
            text_color="#0f1419",
            hover_color="#00a8cc",
            corner_radius=8
        )
        send_btn.pack(side="left", padx=(0, 8))

        clear_btn = ctk.CTkButton(
            button_frame, 
            text="🗑️ Clear", 
            command=self._clear_chat, 
            width=90,
            height=40,
            font=("Segoe UI", 12, "bold"),
            fg_color="#3a4051",
            text_color="#e0e0e0",
            hover_color="#4a5061",
            corner_radius=8
        )
        clear_btn.pack(side="left")

        # ---------- status bar (lower left) ----------
        status_frame = ctk.CTkFrame(self, fg_color="transparent")
        status_frame.pack(fill="x", padx=12, pady=(0, 8))
        
        self.model_label = ctk.CTkLabel(
            status_frame, 
            text=f"📡 Model: {MODEL}", 
            anchor="w", 
            justify="left",
            font=("Segoe UI", 20),
            text_color="#777777"
        )
        self.model_label.pack(side="left")

        # ---------- conversation state ----------
        self.history = []          # will be filled by _load_history()
        self._load_history()

        # Welcome message on fresh start
        if len(self.history) == 1:  # only system prompt present
            welcome = "Good morning, sir. How may I assist you today?"
            self.history.append({"role": "assistant", "content": welcome})
            self._append_to_display(f"J.A.R.V.I.S: {welcome}")

        # Graceful shutdown
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------------
    def _append_to_display(self, txt: str):
        """Insert a line of chat text, handling triple-quote code blocks."""
        txt = txt.rstrip("\n")
        self.chat_display.configure(state="normal")

        # Determine sender and format accordingly
        is_user = txt.startswith("You:")
        is_assistant = txt.startswith("J.A.R.V.I.S:")

        if is_user:
            prefix = "You"
            sender_tag = "user"
            content = txt[5:].lstrip()  # Remove "You: "
            indicator = "👤 "
        elif is_assistant:
            prefix = "J.A.R.V.I.S"
            sender_tag = "assistant"
            content = txt[13:].lstrip()  # Remove "J.A.R.V.I.S: "
            indicator = "🤖 "
        else:
            # System message
            self.chat_display.insert("end", txt + "\n")
            self.chat_display.configure(state="disabled")
            self.chat_display.see("end")
            return

        # Insert formatted message with indicator and sender
        if self._tk_text is not None:
            try:
                self._tk_text.insert("end", indicator, "")
                self._tk_text.insert("end", prefix, sender_tag)
                self._tk_text.insert("end", ": ", "")
            except Exception:
                self.chat_display.insert("end", f"{indicator}{prefix}: ")
        else:
            self.chat_display.insert("end", f"{indicator}{prefix}: ")

        # Insert content, detecting ''' ... ''' or """ ... """
        self._insert_formatted_content(content)

        self.chat_display.configure(state="disabled")
        self.chat_display.see("end")

    # ------------------------------------------------------------------
    def _insert_formatted_content(self, content: str):
        # Look for triple-quote blocks and render them with the "code" tag.
        # Supports language hints like '''python or """javascript.
        
        # Use a simpler approach: find all triple-quoted blocks
        sq_start, dq_start = "'''", chr(34) * 3  # chr(34) = "
        blocks = []
        pos = 0
        
        # Find both single and double triple-quote blocks
        while True:
            sq_idx = content.find(sq_start, pos)
            dq_idx = content.find(dq_start, pos)
            
            if sq_idx == -1 and dq_idx == -1:
                break
            
            if sq_idx != -1 and (dq_idx == -1 or sq_idx < dq_idx):
                # Found single triple-quote first
                end_idx = content.find(sq_start, sq_idx + 3)
                if end_idx != -1:
                    blocks.append((sq_idx, end_idx + 3, sq_start))
                    pos = end_idx + 3
                else:
                    break
            else:
                # Found double triple-quote first
                end_idx = content.find(dq_start, dq_idx + 3)
                if end_idx != -1:
                    blocks.append((dq_idx, end_idx + 3, dq_start))
                    pos = end_idx + 3
                else:
                    break
        
        if not blocks:
            # No code blocks found
            if self._tk_text is not None:
                self._tk_text.insert("end", content)
                self._tk_text.insert("end", "\n")
            else:
                self.chat_display.insert("end", content)
                self.chat_display.insert("end", "\n")
            return
        
        use_tags = self._tk_text is not None and hasattr(self._tk_text, "insert")
        last_end = 0
        
        for start, end, delimiter in blocks:
            # Plain text before this block
            if use_tags:
                self._tk_text.insert("end", content[last_end:start])
            else:
                self.chat_display.insert("end", content[last_end:start])
            
            # Extract code and language
            block_content = content[start + len(delimiter):end - len(delimiter)]
            lines = block_content.split('\n', 1)
            lang = ""
            code = block_content
            
            # Check if first line is a language hint (single word without spaces)
            if lines and len(lines[0].strip()) > 0 and ' ' not in lines[0].strip():
                potential_lang = lines[0].strip()
                if potential_lang and potential_lang.isalnum():
                    lang = potential_lang
                    code = lines[1] if len(lines) > 1 else ""
            
            code = code.strip() if code else ""
            lang_display = f" [{lang}]" if lang else ""
            
            if use_tags:
                try:
                    self._tk_text.insert("end", "\n")
                    self._tk_text.insert("end", "┌─ Code" + lang_display + " " + "─" * max(0, 35 - len(lang_display)), "code")
                    self._tk_text.insert("end", "\n")
                    self._tk_text.insert("end", code, "code")
                    self._tk_text.insert("end", "\n")
                    self._tk_text.insert("end", "└" + "─" * 49, "code")
                    self._tk_text.insert("end", "\n")
                except Exception:
                    self.chat_display.insert("end", f"\n```{lang}\n{code}\n```\n")
            else:
                self.chat_display.insert("end", f"\n```{lang}\n{code}\n```\n")
            
            last_end = end
        
        # Add remaining text
        if use_tags:
            self._tk_text.insert("end", content[last_end:])
            self._tk_text.insert("end", "\n")
        else:
            self.chat_display.insert("end", content[last_end:])
            self.chat_display.insert("end", "\n")

    # ------------------------------------------------------------------
    def _clear_chat(self):
        self.chat_display.configure(state="normal")
        self.chat_display.delete("1.0", "end")
        self.chat_display.configure(state="disabled")
        # keep system prompt; wipe everything else
        self.history = [{"role": "system", "content": SYSTEM_PROMPT}]
        self._append_to_display("💬 Chat cleared. Ready for a fresh conversation.")

    # ------------------------------------------------------------------
    def _on_enter(self, event):
        self._on_send()
        return "break"

    # ------------------------------------------------------------------
    def _on_send(self):
        user_msg = self.entry.get().strip()
        if not user_msg:
            return
        self.entry.delete(0, "end")

        # Replace triple-quote delimiters with markdown fences for the model
        triple_sq = "'''"
        triple_dq = chr(34) * 3  # Three double quotes
        processed_msg = user_msg.replace(triple_sq, "```").replace(triple_dq, "```")
        self.history.append({"role": "user", "content": processed_msg})

        # ---- shortcut handling (file / web) ----
        tool_msg, used_tool = self._handle_shortcuts(user_msg)

        # placeholder while we wait for the answer
        self._append_to_display("J.A.R.V.I.S: ⏳ thinking...")

        # Background thread does the heavy lifting
        threading.Thread(
            target=self._fetch_reply,
            args=(self.history + tool_msg, TOOLS if not used_tool else None),
            daemon=True,
        ).start()

    # ------------------------------------------------------------------
    def _handle_shortcuts(self, user_msg: str) -> tuple[list[dict], bool]:
        """
        Detects slash-commands:
          /file <path>  - reads a local file and injects its content.
          /web <query>  - asks Ollama to perform a web search.
        Returns (tool_message_list, used_tool_flag).
        """
        # /file <path>
        if user_msg.startswith("/file "):
            p = user_msg[6:].strip()
            try:
                content = pathlib.Path(p).read_text(encoding="utf-8")
            except Exception as e:
                return (
                    [
                        {
                            "role": "assistant",
                            "content": f"⚠️  Could not read file: {e}",
                        }
                    ],
                    True,
                )
            self._append_to_display(f"📄 File ({p}) loaded - {len(content)} characters.")
            # Feed the file content as a normal user message (model treats it as context)
            self.history.append(
                {"role": "user", "content": f"File content ({p}):\n{content}"}
            )
            return ([], True)

        # /web <query>
        if user_msg.startswith("/web "):
            query = user_msg[5:].strip()
            tool_msg = [
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_web_1",
                            "type": "function",
                            "function": {
                                "name": "web_search",
                                "arguments": json.dumps({"query": query}),
                            },
                        }
                    ],
                }
            ]
            return (tool_msg, True)

        return ([], False)

    # ------------------------------------------------------------------
    def _fetch_reply(self, messages, tools=None):
        # Remove the placeholder line we added earlier
        self.chat_display.configure(state="normal")
        self.chat_display.delete("end-2l", "end-1l")
        self.chat_display.configure(state="disabled")

        reply = ollama_chat(messages, tools)
        reply = truncate_to_word_limit(reply, 50)   # enforce word limit

        self.history.append({"role": "assistant", "content": reply})
        self._append_to_display(f"J.A.R.V.I.S: {reply}")

    # ------------------------------------------------------------------
    def _load_history(self):
        """Read persisted chat (excluding system prompt)."""
        if self.HISTORY_PATH.is_file():
            try:
                data = json.loads(self.HISTORY_PATH.read_text())
                self.history = [{"role": "system", "content": SYSTEM_PROMPT}] + data
                # Replay saved turns in the UI
                for entry in data:
                    prefix = "You: " if entry["role"] == "user" else "J.A.R.V.I.S: "
                    self._append_to_display(f"{prefix}{entry['content']}")
            except Exception as exc:
                print(f"⚠️  Failed to load history: {exc}")
                self.history = [{"role": "system", "content": SYSTEM_PROMPT}]
        else:
            self.history = [{"role": "system", "content": SYSTEM_PROMPT}]

    # ------------------------------------------------------------------
    def _save_history(self):
        """Write user+assistant turns (skip system prompt) to JSON."""
        to_save = [msg for msg in self.history if msg["role"] != "system"]
        try:
            self.HISTORY_PATH.write_text(json.dumps(to_save, indent=2))
        except Exception as exc:
            print(f"⚠️  Failed to write history: {exc}")

    # ------------------------------------------------------------------
    def _on_close(self):
        self._save_history()
        self.destroy()


def main():
    app = JarvisGUI()
    app.mainloop()

 
if __name__ == "__main__":
    main()
