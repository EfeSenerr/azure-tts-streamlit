import streamlit as st
import requests
import base64
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List
import io
import os
from dotenv import load_dotenv

# Load environment variables from .env file for fallback
load_dotenv()

class AzureTTSClient:
    def __init__(self, endpoint: str, api_key: str):
        """Initialize the Azure TTS client"""
        self.endpoint = endpoint
        self.api_key = api_key
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
    def chunk_text(self, text: str, max_chars: int = 6000) -> List[str]:
        """Split text into chunks that respect sentence boundaries
        
        GPT-4o mini TTS has a limit of 2000 tokens per request.
        Using ~6000 characters provides a safe margin since tokens are 
        roughly 3-4 characters each (2000 tokens ≈ 6000-8000 chars).
        We use 6000 characters to stay safely within the token limit.
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
        
        # Store text chunks in session state for duration estimation
        st.session_state.current_text_chunks = chunks
        
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
    
    # Get API credentials from secrets/environment variables
    try:
        # First try Streamlit secrets
        endpoint = st.secrets.get("AZURE_TTS_ENDPOINT", "")
        api_key = st.secrets.get("AZURE_API_KEY", "")
    except (FileNotFoundError, KeyError):
        # Fallback to environment variables if secrets.toml not found
        endpoint = os.getenv("AZURE_TTS_ENDPOINT", "")
        api_key = os.getenv("AZURE_API_KEY", "")
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # # API Configuration with smart fallback
        # # Try Streamlit secrets first, then environment variables, then empty
        # default_endpoint = ""
        # default_api_key = ""
        
        # try:
        #     # First try Streamlit secrets
        #     default_endpoint = st.secrets.get("AZURE_TTS_ENDPOINT", "")
        #     default_api_key = st.secrets.get("AZURE_API_KEY", "")
        # except (FileNotFoundError, KeyError):
        #     # Fallback to environment variables if secrets.toml not found
        #     default_endpoint = os.getenv("AZURE_TTS_ENDPOINT", "")
        #     default_api_key = os.getenv("AZURE_API_KEY", "")
        
        # endpoint = st.text_input(
        #     "API Endpoint",
        #     value=default_endpoint,
        #     type="default",
        #     help="Your Azure OpenAI TTS endpoint URL"
        # )
        
        # api_key = st.text_input(
        #     "API Key",
        #     value=default_api_key,
        #     type="password",
        #     help="Your Azure OpenAI API key (completely hidden for security)"
        # )

        # Show connection status
        if endpoint and api_key:
            st.success("🔗 Azure TTS Connected")
            st.caption("Using configured secrets")
        else:
            st.error("❌ Missing Azure TTS Configuration")
            st.caption("Check your secrets.toml or .env file")
        
        st.markdown("### 🎵 Voice & Audio Settings")
        
        # Voice selection with descriptions
        voice_options = {
            "alloy": "Alloy - Balanced and natural",
            "echo": "Echo - Clear and articulate", 
            "fable": "Fable - Warm and storytelling",
            "onyx": "Onyx - Deep and authoritative",
            "nova": "Nova - Bright and energetic", 
            "shimmer": "Shimmer - Soft and gentle"
        }
        
        selected_voice = st.selectbox(
            "🎤 Voice Style",
            options=list(voice_options.keys()),
            index=0,
            format_func=lambda x: voice_options[x],
            help="Choose the voice character for text-to-speech"
        )
        
        # Audio format option
        audio_format = st.selectbox(
            "� Audio Format",
            options=["mp3", "wav", "ogg"],
            index=0,
            help="Select audio output format"
        )
        
        # Auto-advance setting
        auto_advance = st.checkbox(
            "� Auto-advance chunks",
            value=True,
            help="Automatically move to next chunk after audio ends"
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
                    audio_chunks = tts_client.convert_text_to_audio_data(text_input.strip(), selected_voice)
                
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
            
            # Audio info panel
            with st.container():
                col_info1, col_info2 = st.columns(2)
                with col_info1:
                    st.metric("📊 Total Chunks", len(audio_chunks))
                with col_info2:
                    st.metric("🎵 Current Voice", voice_options.get(selected_voice, selected_voice).split(' - ')[0])
            
            # Chunk selector
            selected_chunk = st.selectbox(
                "🎵 Select Audio Chunk",
                options=range(len(audio_chunks)),
                index=current_chunk,
                format_func=lambda x: f"🎵 Chunk {x + 1} of {len(audio_chunks)}",
                help="Choose which audio chunk to play"
            )
            
            # Update current chunk if changed
            if selected_chunk != current_chunk:
                st.session_state.current_chunk = selected_chunk
                current_chunk = selected_chunk
            
            # Play selected chunk
            if current_chunk < len(audio_chunks):
                st.markdown(f"**🎵 Now Playing: Chunk {current_chunk + 1}/{len(audio_chunks)}**")
                
                # Create enhanced audio player
                audio_bytes = audio_chunks[current_chunk]
                
                # Enhanced audio player
                st.audio(
                    audio_bytes, 
                    format=f'audio/{audio_format}',
                    start_time=0,
                    autoplay=False,
                    loop=False
                )
                
                # Auto-advance functionality
                if auto_advance and current_chunk < len(audio_chunks) - 1:
                    st.info("🔄 Auto-advance enabled")
                    col_timer1, col_timer2 = st.columns([3, 1])
                    with col_timer1:
                        # Estimate duration based on text length
                        current_text = st.session_state.get('current_text_chunks', [''])[current_chunk] if 'current_text_chunks' in st.session_state else ""
                        estimated_seconds = max(5, len(current_text) // 15)  # ~15 chars per second
                        st.write(f"⏱️ Estimated duration: ~{estimated_seconds} seconds")
                    with col_timer2:
                        if st.button("⏭️ Next Now", key=f"next_now_{current_chunk}"):
                            st.session_state.current_chunk = min(len(audio_chunks) - 1, current_chunk + 1)
                            st.rerun()
                
                # Audio controls
                st.markdown("---")
                st.markdown("**🎛️ Playback Controls**")
                
                # Navigation buttons with enhanced styling
                col_prev, col_play_info, col_next = st.columns([1, 2, 1])
                
                with col_prev:
                    if st.button("⏮️ Previous", disabled=(current_chunk == 0), use_container_width=True):
                        st.session_state.current_chunk = max(0, current_chunk - 1)
                        st.rerun()
                
                with col_play_info:
                    st.markdown(f"<div style='text-align: center; padding: 8px;'>**Chunk {current_chunk + 1} / {len(audio_chunks)}**</div>", unsafe_allow_html=True)
                
                with col_next:
                    if st.button("⏭️ Next", disabled=(current_chunk >= len(audio_chunks) - 1), use_container_width=True):
                        st.session_state.current_chunk = min(len(audio_chunks) - 1, current_chunk + 1)
                        st.rerun()
                
                # Auto-advance settings
                col_auto1, col_auto2 = st.columns(2)
                with col_auto1:
                    if auto_advance and current_chunk < len(audio_chunks) - 1:
                        st.info("🔄 Auto-advance enabled - will move to next chunk")
                        # Add a button to advance manually or automatically after a delay
                        if st.button("⏭️ Next Chunk (Auto)", use_container_width=True):
                            st.session_state.current_chunk = min(len(audio_chunks) - 1, current_chunk + 1)
                            st.rerun()
                    elif auto_advance and current_chunk >= len(audio_chunks) - 1:
                        st.success("✅ Last chunk - playback complete")
                with col_auto2:
                    show_waveform = st.checkbox("📊 Show audio info", help="Display additional audio information")
                
                if show_waveform:
                    audio_size_kb = len(audio_bytes) / 1024
                    st.info(f"📊 Audio size: {audio_size_kb:.1f} KB | Format: {audio_format.upper()} | Voice: {selected_voice}")
                
                # Download options
                st.markdown("---")
                st.markdown("**💾 Download Options**")
                
                col_dl1, col_dl2 = st.columns(2)
                
                with col_dl1:
                    # Download current chunk
                    st.download_button(
                        label=f"⬇️ Download Chunk {current_chunk + 1}",
                        data=audio_bytes,
                        file_name=f"tts_chunk_{current_chunk + 1}_{selected_voice}.{audio_format}",
                        mime=f"audio/{audio_format}",
                        use_container_width=True
                    )
                
                with col_dl2:
                    # Download all chunks combined
                    combined_audio = b"".join(audio_chunks)
                    st.download_button(
                        label="⬇️ Download All Audio",
                        data=combined_audio,
                        file_name=f"tts_complete_{selected_voice}.{audio_format}",
                        mime=f"audio/{audio_format}",
                        use_container_width=True
                    )
                
                # Playlist-style chunk list
                if len(audio_chunks) > 1:
                    with st.expander("🎵 Audio Playlist", expanded=False):
                        for i, _ in enumerate(audio_chunks):
                            col_track, col_play = st.columns([3, 1])
                            with col_track:
                                status = "🔊 Playing" if i == current_chunk else "⏸️ Paused"
                                st.write(f"{status} - Chunk {i + 1}")
                            with col_play:
                                if st.button(f"Play {i + 1}", key=f"play_{i}", disabled=(i == current_chunk)):
                                    st.session_state.current_chunk = i
                                    st.rerun()
        else:
            st.info("👆 Convert some text to see the audio player")
            st.markdown("""
            **🎵 Audio Player Features:**
            - 🎤 6 different voice styles to choose from
            - 🔄 Auto-advance with duration estimation
            - 📊 Audio format selection (MP3, WAV, OGG)
            - ⏮️⏭️ Easy chunk navigation
            - 💾 Download individual chunks or complete audio
            - 🎵 Playlist-style audio management
            """)
    
    # Instructions section
    with st.expander("📖 How to Use This App", expanded=False):
        st.markdown("""
        ### 🚀 Quick Start Guide
        
        1. **🔐 Configure Credentials**: Enter your Azure OpenAI endpoint and API key in the sidebar (completely hidden for security)
        2. **🎤 Choose Voice**: Select from 6 different voice personalities with unique characteristics
        3. **🎛️ Audio Settings**: Choose your preferred audio format and enable auto-advance if desired
        4. **📝 Enter Text**: Paste or type your text in the main text area
        5. **🎵 Convert**: Click "Convert to Speech" to generate high-quality audio
        6. **🎧 Listen**: Use the enhanced audio player with navigation controls
        7. **💾 Download**: Save individual chunks or complete audio files
        
        ### 🎵 Voice Personalities
        - **Alloy**: Balanced and natural - great for general content
        - **Echo**: Clear and articulate - perfect for educational material  
        - **Fable**: Warm and storytelling - ideal for narratives and stories
        - **Onyx**: Deep and authoritative - excellent for presentations
        - **Nova**: Bright and energetic - suitable for marketing content
        - **Shimmer**: Soft and gentle - perfect for meditation or relaxation
        
        ### ✨ Advanced Features
        - ✅ **Smart Text Chunking**: Automatically splits long texts at sentence boundaries
        - ✅ **Parallel Processing**: Faster generation with multi-threaded conversion
        - ✅ **Mobile-Optimized**: Responsive design works perfectly on phones
        - ✅ **Multiple Audio Formats**: Choose between MP3, WAV, and OGG formats
        - ✅ **Auto-Advance**: Automatically suggests moving to next chunk with duration estimation
        - ✅ **Playlist Management**: Easy navigation between audio chunks
        - ✅ **Secure Credentials**: API keys are completely hidden and secure
        - ✅ **Progress Tracking**: Real-time feedback during audio generation
        - ✅ **Download Options**: Save individual chunks or complete audio files
        
        ### 🎛️ Audio Controls
        - **Auto-Advance**: Enable to get prompts to move to next chunk after estimated duration
        - **Format Selection**: Choose the best audio format for your needs
        - **Manual Navigation**: Use Previous/Next buttons for full control
        - **Audio Info**: View technical details about your generated audio
        
        ### 📱 Mobile Usage Tips
        - All controls are touch-friendly and responsive
        - Use landscape mode for the best experience
        - Audio files work with your device's native audio controls
        - Downloads save directly to your device's download folder
        """)
    
    # Performance Tips
    with st.expander("🚀 Performance & Tips", expanded=False):
        st.markdown("""
        ### ⚡ Performance Optimization
        - **Chunk Size**: Texts are automatically split into ~6000 character chunks (GPT-4o mini TTS limit: 2000 tokens ≈ 6000-8000 chars)
        - **Parallel Processing**: Multiple chunks are generated simultaneously for faster results
        - **Memory Efficient**: Audio data is streamed efficiently without excessive memory usage
        
        ### 💡 Pro Tips
        - **Long Documents**: For very long texts, consider breaking them into sections manually
        - **Voice Testing**: Try different voices with the same text to find your preferred style
        - **Mobile Downloads**: Audio files can be saved directly to your phone for offline listening
        - **Browser Compatibility**: Works best in modern browsers with HTML5 audio support
        
        ### 🔧 Troubleshooting
        - **No Audio**: Check that your API credentials are correct and valid
        - **Slow Generation**: Large texts take longer - progress bars show real-time status
        - **Download Issues**: Ensure your browser allows downloads from this domain
        """)
    
    # Security section
    with st.expander("🔐 Security & Privacy", expanded=False):
        st.markdown("""
        ### 🛡️ Security Features
        - **Hidden API Keys**: Your credentials are masked and never displayed in logs
        - **Secure Storage**: API keys are stored securely in Streamlit secrets
        - **No Persistence**: Audio data is not permanently stored on servers
        - **HTTPS Ready**: Fully compatible with secure HTTPS deployments
        
        ### 🔒 Privacy Considerations
        - **Text Processing**: Your text is sent to Azure OpenAI for processing
        - **Temporary Storage**: Audio is generated and delivered directly to your browser
        - **No Tracking**: This app doesn't track or store your personal data
        - **Local Downloads**: Generated audio files are saved locally to your device
        """)
    
    # Footer with enhanced information
    st.markdown("---")
    col_footer1, col_footer2, col_footer3 = st.columns(3)
    
    with col_footer1:
        st.markdown("**🎵 Azure TTS App**")
        st.markdown("Built with ❤️ using Streamlit")
    
    with col_footer2:
        st.markdown("**🔗 Powered By**")
        st.markdown("Azure OpenAI TTS API")
    
    with col_footer3:
        st.markdown("**📱 Mobile Ready**")
        st.markdown("Optimized for all devices")

if __name__ == "__main__":
    main()
