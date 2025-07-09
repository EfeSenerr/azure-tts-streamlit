import streamlit as st
import requests
import base64
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List
import io

class AzureTTSClient:
    def __init__(self, endpoint: str, api_key: str):
        """Initialize the Azure TTS client"""
        self.endpoint = endpoint
        self.api_key = api_key
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
    def chunk_text(self, text: str, max_chars: int = 4000) -> List[str]:
        """Split text into chunks that respect sentence boundaries"""
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
        """Convert text to speech using Azure OpenAI TTS API"""
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
    
    def convert_text_to_audio_data(self, text: str, voice: str = "alloy", max_workers: int = 3) -> List[bytes]:
        """Convert text to speech and return list of audio data as bytes"""
        chunks = self.chunk_text(text)
        st.info(f"Text split into {len(chunks)} chunks")
        
        # Create progress bar
        progress_bar = st.progress(0)
        completed_chunks = 0
        
        # Submit all chunks for processing in parallel
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
                    completed_chunks += 1
                    progress_bar.progress(completed_chunks / len(chunks))
                    st.write(f"✅ Chunk {index + 1}/{len(chunks)} processed")
                except Exception as e:
                    st.error(f"❌ Error processing chunk {index + 1}: {e}")
                    results[index] = None
        
        progress_bar.empty()
        
        # Filter out None results
        audio_chunks = [audio for audio in results if audio is not None]
        return audio_chunks

def main():
    st.set_page_config(
        page_title="🎵 Azure TTS App",
        page_icon="🎵",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.title("🎵 Azure Text-to-Speech App")
    st.markdown("Convert text to natural-sounding speech using Azure OpenAI's TTS API")
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # API Configuration
        endpoint = st.text_input(
            "API Endpoint",
            value="https://sener-mcryr3zf-eastus2.openai.azure.com/openai/deployments/gpt-4o-mini-tts/audio/speech?api-version=2025-03-01-preview",
            type="default"
        )
        
        api_key = st.text_input(
            "API Key",
            value="FLF9WIzEk4XuP61sqWHbG9a8P8wzsOSkgPdXKpDeBqyTMLaEXL2QJQQJ99BGACHYHv6XJ3w3AAAAACOGSuop",
            type="password"
        )
        
        voice = st.selectbox(
            "Voice",
            options=["alloy", "echo", "fable", "onyx", "nova", "shimmer"],
            index=0
        )
        
        st.markdown("---")
        st.markdown("### 📱 Mobile Friendly")
        st.markdown("This app works great on phones!")
        
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("📝 Text Input")
        text_input = st.text_area(
            "Enter your text to convert to speech:",
            value="""Welcome to the Azure Text-to-Speech Streamlit demo! This application uses Azure OpenAI's TTS API to convert your text into natural-sounding speech. 

You can paste any text here, and the application will automatically split it into chunks if it's longer than 4000 characters. The chunks are processed in parallel for faster generation.

Try pasting a long article or story to see how the chunking and parallel processing works!""",
            height=200
        )
        
        # Convert button
        if st.button("🎵 Convert to Speech", type="primary", use_container_width=True):
            if not endpoint or not api_key:
                st.error("Please provide both API endpoint and key in the sidebar")
                return
            
            if not text_input.strip():
                st.error("Please enter some text to convert")
                return
            
            try:
                # Initialize TTS client
                with st.spinner("Initializing TTS client..."):
                    tts_client = AzureTTSClient(endpoint, api_key)
                
                # Convert text to audio
                with st.spinner("Converting text to speech..."):
                    audio_chunks = tts_client.convert_text_to_audio_data(text_input.strip(), voice)
                
                if not audio_chunks:
                    st.error("Failed to generate audio")
                    return
                
                st.success(f"✅ Audio conversion completed! Generated {len(audio_chunks)} chunks.")
                
                # Store audio chunks in session state
                st.session_state.audio_chunks = audio_chunks
                st.session_state.current_chunk = 0
                
            except Exception as e:
                st.error(f"❌ TTS conversion failed: {str(e)}")
    
    with col2:
        st.header("🎵 Audio Player")
        
        if 'audio_chunks' in st.session_state and st.session_state.audio_chunks:
            audio_chunks = st.session_state.audio_chunks
            current_chunk = st.session_state.get('current_chunk', 0)
            
            st.info(f"📊 Total chunks: {len(audio_chunks)}")
            
            # Chunk selector
            selected_chunk = st.selectbox(
                "Select chunk to play:",
                options=range(len(audio_chunks)),
                index=current_chunk,
                format_func=lambda x: f"Chunk {x + 1}"
            )
            
            # Update current chunk if changed
            if selected_chunk != current_chunk:
                st.session_state.current_chunk = selected_chunk
                current_chunk = selected_chunk
            
            # Play selected chunk
            if current_chunk < len(audio_chunks):
                st.markdown(f"**🎵 Playing Chunk {current_chunk + 1}/{len(audio_chunks)}**")
                
                # Create audio player
                audio_bytes = audio_chunks[current_chunk]
                st.audio(audio_bytes, format='audio/mp3')
                
                # Navigation buttons
                col_prev, col_next = st.columns(2)
                
                with col_prev:
                    if st.button("⏮️ Previous", disabled=(current_chunk == 0)):
                        st.session_state.current_chunk = max(0, current_chunk - 1)
                        st.rerun()
                
                with col_next:
                    if st.button("⏭️ Next", disabled=(current_chunk >= len(audio_chunks) - 1)):
                        st.session_state.current_chunk = min(len(audio_chunks) - 1, current_chunk + 1)
                        st.rerun()
                
                # Download options
                st.markdown("---")
                st.markdown("**💾 Download Options:**")
                
                # Download current chunk
                st.download_button(
                    label=f"⬇️ Download Chunk {current_chunk + 1}",
                    data=audio_bytes,
                    file_name=f"tts_chunk_{current_chunk + 1}.mp3",
                    mime="audio/mp3"
                )
                
                # Download all chunks as zip (simplified - just current for now)
                st.download_button(
                    label="⬇️ Download All Audio",
                    data=b"".join(audio_chunks),
                    file_name="tts_complete_audio.mp3",
                    mime="audio/mp3"
                )
        else:
            st.info("👆 Convert some text to see the audio player")
    
    # Instructions section
    with st.expander("📖 How to Use"):
        st.markdown("""
        1. **Configure**: Enter your Azure OpenAI endpoint and API key in the sidebar
        2. **Select Voice**: Choose from 6 available voices (alloy, echo, fable, onyx, nova, shimmer)
        3. **Enter Text**: Paste or type your text in the text area
        4. **Convert**: Click "Convert to Speech" to generate audio
        5. **Play**: Use the audio player to listen to individual chunks or navigate between them
        6. **Download**: Save individual chunks or the complete audio file
        
        **Features:**
        - ✅ Automatic text chunking for long texts
        - ✅ Parallel processing for faster generation
        - ✅ Mobile-friendly interface
        - ✅ Multiple voice options
        - ✅ Chunk navigation and download
        """)
    
    # Footer
    st.markdown("---")
    st.markdown("Built with ❤️ using Streamlit and Azure OpenAI TTS")

if __name__ == "__main__":
    main()
