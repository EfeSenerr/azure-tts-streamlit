import os
import requests
import json
import pygame
import io
import threading
import time
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple
import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk

class AzureTTSClient:
    def __init__(self, endpoint: str, api_key: str):
        """
        Initialize the Azure TTS client
        
        Args:
            endpoint: Azure OpenAI TTS endpoint URL
            api_key: API key for authentication
        """
        self.endpoint = endpoint
        self.api_key = api_key
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        # Initialize pygame mixer for audio playback
        pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
        
    def chunk_text(self, text: str, max_chars: int = 4000) -> List[str]:
        """
        Split text into chunks that respect sentence boundaries
        
        Args:
            text: Input text to chunk
            max_chars: Maximum characters per chunk
            
        Returns:
            List of text chunks
        """
        if len(text) <= max_chars:
            return [text]
        
        chunks = []
        current_chunk = ""
        
        # Split by sentences first
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        for sentence in sentences:
            # If a single sentence is too long, split by words
            if len(sentence) > max_chars:
                words = sentence.split()
                temp_chunk = ""
                
                for word in words:
                    if len(temp_chunk + " " + word) <= max_chars:
                        temp_chunk += (" " + word) if temp_chunk else word
                    else:
                        if temp_chunk:
                            chunks.append(temp_chunk.strip())
                        temp_chunk = word
                
                if temp_chunk:
                    if len(current_chunk + " " + temp_chunk) <= max_chars:
                        current_chunk += (" " + temp_chunk) if current_chunk else temp_chunk
                    else:
                        if current_chunk:
                            chunks.append(current_chunk.strip())
                        current_chunk = temp_chunk
            else:
                # Check if adding this sentence exceeds the limit
                if len(current_chunk + " " + sentence) <= max_chars:
                    current_chunk += (" " + sentence) if current_chunk else sentence
                else:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = sentence
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def text_to_speech(self, text: str, voice: str = "alloy") -> bytes:
        """
        Convert text to speech using Azure OpenAI TTS API
        
        Args:
            text: Text to convert
            voice: Voice to use (alloy, echo, fable, onyx, nova, shimmer)
            
        Returns:
            Audio data as bytes
        """
        payload = {
            "model": "gpt-4o-mini-tts",
            "input": text,
            "voice": voice
        }
        
        try:
            response = requests.post(
                self.endpoint,
                headers=self.headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            return response.content
        except requests.exceptions.RequestException as e:
            raise Exception(f"TTS API request failed: {str(e)}")
    
    def play_audio(self, audio_data: bytes):
        """Play audio data using pygame"""
        try:
            audio_file = io.BytesIO(audio_data)
            pygame.mixer.music.load(audio_file)
            pygame.mixer.music.play()
            
            # Wait for playback to finish
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
        except Exception as e:
            raise Exception(f"Audio playback failed: {str(e)}")
    
    def convert_and_play_parallel(self, text: str, voice: str = "alloy", max_workers: int = 3):
        """
        Convert text to speech with parallel processing and sequential playback
        
        Args:
            text: Input text
            voice: Voice to use
            max_workers: Maximum number of parallel API calls
        """
        chunks = self.chunk_text(text)
        print(f"Text split into {len(chunks)} chunks")
        
        # Submit all chunks for processing in parallel
        audio_queue = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all chunks
            future_to_index = {
                executor.submit(self.text_to_speech, chunk, voice): i 
                for i, chunk in enumerate(chunks)
            }
            
            # Collect results in order
            results = [None] * len(chunks)
            
            for future in as_completed(future_to_index):
                index = future_to_index[future]
                try:
                    audio_data = future.result()
                    results[index] = audio_data
                    print(f"Chunk {index + 1}/{len(chunks)} processed")
                except Exception as e:
                    print(f"Error processing chunk {index + 1}: {e}")
                    results[index] = None
        
        # Play audio chunks in order
        print("Starting playback...")
        for i, audio_data in enumerate(results):
            if audio_data:
                print(f"Playing chunk {i + 1}/{len(chunks)}")
                self.play_audio(audio_data)
            else:
                print(f"Skipping chunk {i + 1} due to processing error")

class TTSInterface:
    def __init__(self):
        """Initialize the GUI interface"""
        self.root = tk.Tk()
        self.root.title("Azure TTS Client")
        self.root.geometry("800x600")
        
        # Initialize TTS client (will be set up after configuration)
        self.tts_client = None
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the user interface"""
        # Configuration frame
        config_frame = ttk.LabelFrame(self.root, text="Configuration", padding="10")
        config_frame.pack(fill="x", padx=10, pady=5)
        
        # API Endpoint
        ttk.Label(config_frame, text="API Endpoint:").grid(row=0, column=0, sticky="w", pady=2)
        self.endpoint_var = tk.StringVar(value="https://YOUR-RESOURCE.openai.azure.com/openai/deployments/YOUR-DEPLOYMENT/audio/speech?api-version=2025-03-01-preview")
        endpoint_entry = ttk.Entry(config_frame, textvariable=self.endpoint_var, width=80)
        endpoint_entry.grid(row=0, column=1, pady=2, padx=5)
        
        # API Key
        ttk.Label(config_frame, text="API Key:").grid(row=1, column=0, sticky="w", pady=2)
        self.api_key_var = tk.StringVar(value="YOUR_API_KEY_HERE")
        api_key_entry = ttk.Entry(config_frame, textvariable=self.api_key_var, width=80, show="*")
        api_key_entry.grid(row=1, column=1, pady=2, padx=5)
        
        # Voice selection
        ttk.Label(config_frame, text="Voice:").grid(row=2, column=0, sticky="w", pady=2)
        self.voice_var = tk.StringVar(value="alloy")
        voice_combo = ttk.Combobox(config_frame, textvariable=self.voice_var, 
                                  values=["alloy", "echo", "fable", "onyx", "nova", "shimmer"],
                                  state="readonly", width=15)
        voice_combo.grid(row=2, column=1, sticky="w", pady=2, padx=5)
        
        # Initialize button
        init_btn = ttk.Button(config_frame, text="Initialize TTS Client", command=self.initialize_client)
        init_btn.grid(row=3, column=1, sticky="w", pady=10, padx=5)
        
        # Text input frame
        text_frame = ttk.LabelFrame(self.root, text="Text Input", padding="10")
        text_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Text area
        self.text_area = scrolledtext.ScrolledText(text_frame, wrap=tk.WORD, height=15)
        self.text_area.pack(fill="both", expand=True)
        
        # Insert sample text
        sample_text = """Welcome to the Azure Text-to-Speech demo! This application uses Azure OpenAI's TTS API to convert your text into natural-sounding speech. 

You can paste any text here, and the application will automatically split it into chunks if it's longer than 4000 characters. The chunks are processed in parallel for faster generation, but played back sequentially to maintain the natural flow of speech.

Try pasting a long article or story to see how the chunking and parallel processing works!"""
        
        self.text_area.insert("1.0", sample_text)
        
        # Control frame
        control_frame = ttk.Frame(self.root)
        control_frame.pack(fill="x", padx=10, pady=5)
        
        # Buttons
        self.speak_btn = ttk.Button(control_frame, text="Convert & Play", command=self.convert_and_play, state="disabled")
        self.speak_btn.pack(side="left", padx=5)
        
        self.stop_btn = ttk.Button(control_frame, text="Stop", command=self.stop_audio)
        self.stop_btn.pack(side="left", padx=5)
        
        self.clear_btn = ttk.Button(control_frame, text="Clear Text", command=self.clear_text)
        self.clear_btn.pack(side="left", padx=5)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready - Please initialize TTS client first")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief="sunken")
        status_bar.pack(fill="x", padx=10, pady=5)
        
    def initialize_client(self):
        """Initialize the TTS client with current configuration"""
        try:
            endpoint = self.endpoint_var.get().strip()
            api_key = self.api_key_var.get().strip()
            
            if not endpoint or not api_key:
                messagebox.showerror("Error", "Please provide both endpoint and API key")
                return
            
            self.tts_client = AzureTTSClient(endpoint, api_key)
            self.speak_btn.config(state="normal")
            self.status_var.set("TTS Client initialized successfully")
            messagebox.showinfo("Success", "TTS Client initialized successfully!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to initialize TTS client: {str(e)}")
            self.status_var.set("Initialization failed")
    
    def convert_and_play(self):
        """Convert text to speech and play"""
        if not self.tts_client:
            messagebox.showerror("Error", "Please initialize TTS client first")
            return
        
        text = self.text_area.get("1.0", tk.END).strip()
        if not text:
            messagebox.showwarning("Warning", "Please enter some text")
            return
        
        self.speak_btn.config(state="disabled")
        self.status_var.set("Processing...")
        
        # Run TTS in a separate thread to avoid blocking the UI
        def tts_thread():
            try:
                voice = self.voice_var.get()
                self.tts_client.convert_and_play_parallel(text, voice)
                self.status_var.set("Playback completed")
            except Exception as e:
                messagebox.showerror("Error", f"TTS failed: {str(e)}")
                self.status_var.set("Error occurred")
            finally:
                self.speak_btn.config(state="normal")
        
        threading.Thread(target=tts_thread, daemon=True).start()
    
    def stop_audio(self):
        """Stop audio playback"""
        try:
            pygame.mixer.music.stop()
            self.status_var.set("Playback stopped")
        except:
            pass
    
    def clear_text(self):
        """Clear the text area"""
        self.text_area.delete("1.0", tk.END)
    
    def run(self):
        """Start the GUI application"""
        self.root.mainloop()

# Quick test function for command-line usage
def quick_test():
    """Quick test function for command-line usage"""
    endpoint = "https://YOUR-RESOURCE.openai.azure.com/openai/deployments/YOUR-DEPLOYMENT/audio/speech?api-version=2025-03-01-preview"
    api_key = "YOUR_API_KEY_HERE"
    
    # Create TTS client
    tts = AzureTTSClient(endpoint, api_key)
    
    # Test with a short text
    test_text = "Hello! This is a test of the Azure TTS API. The quick brown fox jumped over the lazy dog."
    
    print("Converting text to speech...")
    try:
        tts.convert_and_play_parallel(test_text)
        print("Test completed successfully!")
    except Exception as e:
        print(f"Test failed: {e}")

if __name__ == "__main__":
    # You can run the GUI interface or the quick test
    print("Azure TTS Client")
    print("1. Run GUI interface")
    print("2. Run quick test")
    
    choice = input("Enter your choice (1 or 2): ").strip()
    
    if choice == "2":
        quick_test()
    else:
        # Run GUI interface
        app = TTSInterface()
        app.run()
