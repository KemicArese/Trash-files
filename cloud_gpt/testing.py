import tkinter as tk
from tkinter import scrolledtext, Entry, Button, END, Frame, PhotoImage
import requests
import json
import threading
from datetime import datetime
import speech_recognition as sr
from gtts import gTTS
import pygame
import os
import tempfile

class CURCUIT:
    def __init__(self, root):
        self.root = root
        self.root.title("CURCUIT - Ollama Assistant")
        self.root.geometry("1000x700")
        self.root.configure(bg="#1e1e2e")
        self.root.minsize(800, 600)
        
        # Voice functionality
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.is_listening = False
        self.voice_enabled = True
        
        # Initialize pygame mixer for audio
        pygame.mixer.init()
        
        # Create GUI components
        self.create_widgets()
        
        # Ollama API configuration
        self.api_url = "http://localhost:11434/api/generate"
        self.model = "qwen3-coder:480b-cloud"
        
        # Adjust for ambient noise
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source)
        
    def create_widgets(self):
        # Header
        header_frame = tk.Frame(self.root, bg="#121212", height=70)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)
        
        title_frame = tk.Frame(header_frame, bg="#121212")
        title_frame.pack(pady=15)
        
        header_label = tk.Label(
            title_frame, 
            text="CURCUIT", 
            font=("Segoe UI", 20, "bold"),
            fg="#5de4c7",
            bg="#121212"
        )
        header_label.pack(side=tk.LEFT, padx=(20, 0))
        
        subtitle_label = tk.Label(
            title_frame,
            text="Ollama Assistant with Voice",
            font=("Segoe UI", 12),
            fg="#8d8d8d",
            bg="#121212"
        )
        subtitle_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # Voice control buttons
        voice_frame = tk.Frame(header_frame, bg="#121212")
        voice_frame.pack(side=tk.RIGHT, padx=20)
        
        self.voice_button = Button(
            voice_frame,
            text="🎤 Voice Input",
            command=self.toggle_voice_input,
            bg="#5de4c7",
            fg="#121212",
            font=("Segoe UI", 10, "bold"),
            relief=tk.FLAT,
            activebackground="#4bc9b0",
            activeforeground="#121212",
            cursor="hand2"
        )
        self.voice_button.pack(side=tk.LEFT, padx=5)
        
        self.speak_button = Button(
            voice_frame,
            text="🔊 Voice Output",
            command=self.toggle_voice_output,
            bg="#5de4c7",
            fg="#121212",
            font=("Segoe UI", 10, "bold"),
            relief=tk.FLAT,
            activebackground="#4bc9b0",
            activeforeground="#121212",
            cursor="hand2"
        )
        self.speak_button.pack(side=tk.LEFT, padx=5)
        
        # Status bar
        self.status_frame = tk.Frame(self.root, bg="#252536", height=30)
        self.status_frame.pack(fill=tk.X)
        self.status_frame.pack_propagate(False)
        
        self.status_label = tk.Label(
            self.status_frame,
            text="Ready",
            font=("Segoe UI", 9),
            fg="#a0a0a0",
            bg="#252536"
        )
        self.status_label.pack(side=tk.LEFT, padx=10, pady=5)
        
        # Chat container
        chat_container = tk.Frame(self.root, bg="#1e1e2e")
        chat_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # Chat history display with custom tags for styling
        self.chat_history = scrolledtext.ScrolledText(
            chat_container, 
            wrap=tk.WORD,
            bg="#252536", 
            fg="#e0e0e0",
            font=("Segoe UI", 11),
            relief=tk.FLAT,
            padx=20,
            pady=20,
            spacing2=8
        )
        self.chat_history.pack(fill=tk.BOTH, expand=True)
        
        # Configure text tags for styling
        self.chat_history.tag_configure("user_name", foreground="#5de4c7", font=("Segoe UI", 11, "bold"))
        self.chat_history.tag_configure("assistant_name", foreground="#89b4fa", font=("Segoe UI", 11, "bold"))
        self.chat_history.tag_configure("user_message", foreground="#ffffff", lmargin1=30, lmargin2=30)
        self.chat_history.tag_configure("assistant_message", foreground="#cbd5e1", lmargin1=30, lmargin2=30)
        self.chat_history.tag_configure("timestamp", foreground="#7d7d7d", font=("Segoe UI", 8))
        self.chat_history.tag_configure("divider", foreground="#3a3a4a")
        self.chat_history.tag_configure("status", foreground="#a0a0a0", font=("Segoe UI", 9, "italic"))
        
        # Disable editing
        self.chat_history.config(state='disabled')
        
        # User input frame
        input_frame = tk.Frame(self.root, bg="#1e1e2e")
        input_frame.pack(fill=tk.X, padx=15, pady=(0, 15))
        
        # User input field
        self.user_input = Entry(
            input_frame, 
            font=("Segoe UI", 12),
            bg="#2d2d3d",
            fg="#ffffff",
            insertbackground="#5de4c7",
            relief=tk.FLAT,
            highlightthickness=0
        )
        self.user_input.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=12, ipadx=15)
        self.user_input.bind("<Return>", self.send_message)
        self.user_input.focus()
        
        # Voice input button
        self.mic_button = Button(
            input_frame,
            text="🎤",
            command=self.start_voice_input,
            bg="#2d2d3d",
            fg="#5de4c7",
            font=("Segoe UI", 14),
            relief=tk.FLAT,
            activebackground="#3a3a4a",
            activeforeground="#5de4c7",
            cursor="hand2",
            width=4
        )
        self.mic_button.pack(side=tk.LEFT, padx=(10, 0), ipady=3)
        
        # Send button
        self.send_button = Button(
            input_frame,
            text="Send",
            command=self.send_message,
            bg="#5de4c7",
            fg="#121212",
            font=("Segoe UI", 10, "bold"),
            relief=tk.FLAT,
            activebackground="#4bc9b0",
            activeforeground="#121212",
            cursor="hand2"
        )
        self.send_button.pack(side=tk.RIGHT, padx=(10, 0), ipadx=25, ipady=8)
        
        # Initial message
        self.display_message("assistant", "Hello! I'm CURCUIT, your Ollama coding assistant. How can I help you today?")
        self.display_status("Voice input is enabled. Click the microphone to speak.")
        
    def display_message(self, sender, message):
        self.chat_history.config(state='normal')
        
        # Get current timestamp
        timestamp = datetime.now().strftime("%H:%M")
        
        if sender == "user":
            # User message styling
            self.chat_history.insert(tk.END, "You ", "user_name")
            self.chat_history.insert(tk.END, f"  {timestamp}\n", "timestamp")
            self.chat_history.insert(tk.END, f"{message}\n\n", "user_message")
        else:
            # Assistant message styling
            self.chat_history.insert(tk.END, "CURCUIT ", "assistant_name")
            self.chat_history.insert(tk.END, f"  {timestamp}\n", "timestamp")
            self.chat_history.insert(tk.END, f"{message}\n\n", "assistant_message")
            
        # Add divider line
        self.chat_history.insert(tk.END, "—" * 100 + "\n", "divider")
        
        self.chat_history.config(state='disabled')
        self.chat_history.yview(tk.END)
        
    def display_status(self, message):
        self.chat_history.config(state='normal')
        self.chat_history.insert(tk.END, f"{message}\n", "status")
        self.chat_history.config(state='disabled')
        self.chat_history.yview(tk.END)
        
    def update_status(self, message):
        self.status_label.config(text=message)
        
    def send_message(self, event=None):
        user_message = self.user_input.get().strip()
        if not user_message:
            return
            
        # Display user message
        self.display_message("user", user_message)
        self.user_input.delete(0, END)
        
        # Disable input while processing
        self.user_input.config(state='disabled')
        self.send_button.config(state='disabled', text="Processing...", bg="#3a3a4a")
        self.mic_button.config(state='disabled')
        
        # Process in separate thread to prevent UI freezing
        threading.Thread(target=self.get_ollama_response, args=(user_message,), daemon=True).start()
        
    def get_ollama_response(self, user_message):
        try:
            self.update_status("Processing your request...")
            
            # Prepare the request payload
            payload = {
                "model": self.model,
                "prompt": user_message,
                "stream": False
            }
            
            # Send request to Ollama API
            response = requests.post(
                self.api_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=120
            )
            
            # Process response
            if response.status_code == 200:
                result = response.json()
                assistant_message = result.get("response", "Sorry, I couldn't process that.")
            else:
                assistant_message = f"Error: {response.status_code} - {response.text}"
                
        except requests.exceptions.RequestException as e:
            assistant_message = f"Connection error: {str(e)}"
        except json.JSONDecodeError:
            assistant_message = "Error: Invalid response format"
        except Exception as e:
            assistant_message = f"Unexpected error: {str(e)}"
            
        # Display response in main thread
        self.root.after(0, self.display_response, assistant_message)
        
    def display_response(self, message):
        self.display_message("assistant", message)
        self.user_input.config(state='normal')
        self.send_button.config(state='normal', text="Send", bg="#5de4c7")
        self.mic_button.config(state='normal')
        self.update_status("Ready")
        
        # Speak the response if voice output is enabled
        if self.voice_enabled:
            threading.Thread(target=self.speak_text, args=(message,), daemon=True).start()
        
    def toggle_voice_input(self):
        self.is_listening = not self.is_listening
        if self.is_listening:
            self.voice_button.config(bg="#ff6b6b", text="🔇 Voice Input OFF")
            self.display_status("Voice input disabled")
        else:
            self.voice_button.config(bg="#5de4c7", text="🎤 Voice Input ON")
            self.display_status("Voice input enabled")
            
    def toggle_voice_output(self):
        self.voice_enabled = not self.voice_enabled
        if self.voice_enabled:
            self.speak_button.config(bg="#5de4c7", text="🔊 Voice Output ON")
            self.display_status("Voice output enabled")
        else:
            self.speak_button.config(bg="#ff6b6b", text="🔇 Voice Output OFF")
            self.display_status("Voice output disabled")
            
    def start_voice_input(self):
        if self.is_listening:
            return
            
        self.update_status("Listening...")
        self.display_status("Listening... Speak now")
        self.mic_button.config(bg="#ff6b6b", fg="#ffffff")
        
        # Start listening in a separate thread
        threading.Thread(target=self.process_voice_input, daemon=True).start()
        
    def process_voice_input(self):
        try:
            with self.microphone as source:
                audio = self.recognizer.listen(source, timeout=5)
                
            self.update_status("Processing speech...")
            self.display_status("Processing speech...")
            
            # Recognize speech using Google Speech Recognition
            text = self.recognizer.recognize_google(audio)
            
            # Update UI in main thread
            self.root.after(0, self.handle_voice_input, text)
            
        except sr.WaitTimeoutError:
            self.root.after(0, self.handle_voice_error, "Listening timed out")
        except sr.UnknownValueError:
            self.root.after(0, self.handle_voice_error, "Could not understand audio")
        except sr.RequestError as e:
            self.root.after(0, self.handle_voice_error, f"Could not request results; {e}")
        except Exception as e:
            self.root.after(0, self.handle_voice_error, f"Error: {str(e)}")
            
    def handle_voice_input(self, text):
        self.user_input.delete(0, END)
        self.user_input.insert(0, text)
        self.mic_button.config(bg="#2d2d3d", fg="#5de4c7")
        self.update_status("Ready")
        self.display_status(f"Recognized: {text}")
        self.send_message()
        
    def handle_voice_error(self, error_message):
        self.mic_button.config(bg="#2d2d3d", fg="#5de4c7")
        self.update_status("Ready")
        self.display_status(f"Voice input error: {error_message}")
        
    def speak_text(self, text):
        try:
            self.update_status("Speaking...")
            
            # Create a temporary file for the audio
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
                temp_filename = fp.name
                
            # Generate speech
            tts = gTTS(text, lang='en')
            tts.save(temp_filename)
            
            # Play the audio
            pygame.mixer.music.load(temp_filename)
            pygame.mixer.music.play()
            
            # Wait for playback to finish
            while pygame.mixer.music.get_busy():
                continue
                
            # Clean up temporary file
            os.unlink(temp_filename)
            
            self.update_status("Ready")
        except Exception as e:
            self.update_status("Ready")
            self.display_status(f"Text-to-speech error: {str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = CURCUIT(root)
    root.mainloop()
