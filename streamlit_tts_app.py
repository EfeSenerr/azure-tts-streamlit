import streamlit as st
import requests
import base64
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List
import io
import os
from dotenv import load_dotenv

# Load environment variables from .env file for  
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
    
    def convert_text_to_audio_data(self, text: str, voice: str = "alloy", max_workers: int = 3) -> bytes:
        """Convert text to speech and return combined audio data as bytes"""
        chunks = self.chunk_text(text)
        
        if len(chunks) > 1:
            st.info(f"Processing text in {len(chunks)} parts for optimal quality...")
        
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
                    st.write(f"✅ Part {index + 1}/{len(chunks)} completed")
                except Exception as e:
                    st.error(f"❌ Error processing part {index + 1}: {e}")
                    results[index] = None
        
        progress_bar.empty()
        
        # Filter out None results
        audio_chunks = [audio for audio in results if audio is not None]
        
        if not audio_chunks:
            raise Exception("No audio chunks were successfully generated")
        
        # Combine all chunks into a single audio file
        if len(audio_chunks) > 1:
            st.info("Combining audio parts into seamless speech...")
            combined_audio = self.combine_audio_chunks(audio_chunks)
        else:
            combined_audio = audio_chunks[0]
        
        return combined_audio
    
    def combine_audio_chunks(self, audio_chunks: List[bytes]) -> bytes:
        """Combine multiple audio chunks into a single seamless audio file"""
        if not audio_chunks:
            return b""
        
        if len(audio_chunks) == 1:
            return audio_chunks[0]
        
        # For MP3 files, we can simply concatenate the bytes
        # This works because MP3 is designed to be streamable
        combined_audio = b"".join(audio_chunks)
        return combined_audio

def main():
    st.set_page_config(
        page_title="Podcast Maker 🎧",
        page_icon="🎵",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.title("🎵 Podcast Maker 🎧")
    st.markdown("""Welcome to the Podcast Maker! This application uses Azure OpenAI's TTS API to convert your text into natural-sounding speech. 
                You can paste any text here, and the application will automatically process it to create seamless, high-quality audio. Long texts are handled intelligently behind the scenes for optimal results.""")
    
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
            "🎵 Audio Format",
            options=["mp3", "wav", "ogg"],
            index=0,
            help="Select audio output format"
        )
        
        # Auto-play setting
        auto_play = st.checkbox(
            "🔊 Auto-play audio",
            value=True,
            help="Automatically start playing audio after conversion"
        )
        
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("📝 Text Input")
        text_input = st.text_area(
            "Enter your text to convert to speech:",
            value="""You can paste any text here.""",
            height=200
        )

        # Safety: Limit input to ~10 pages (about 30,000 characters)
        MAX_INPUT_CHARS = 50000  # ~10 pages (assuming 3000 chars/page)
        if len(text_input) > MAX_INPUT_CHARS:
            st.warning(f"⚠️ Input too long! Please limit your text to about 10 pages (~{MAX_INPUT_CHARS} characters). You entered {len(text_input):,} characters.")
        
        # Convert button
        if st.button("🎵 Convert to Speech", type="primary", use_container_width=True):
            if not endpoint or not api_key:
                st.error("Please provide both API endpoint and key in the sidebar")
                return

            if not text_input.strip():
                st.error("Please enter some text to convert")
                return

            if len(text_input) > MAX_INPUT_CHARS:
                st.error(f"❌ Input too long! Please limit your text to about 10 pages (~{MAX_INPUT_CHARS} characters). You entered {len(text_input):,} characters.")
                return

            try:
                # Initialize TTS client
                with st.spinner("Initializing TTS client..."):
                    tts_client = AzureTTSClient(endpoint, api_key)

                # Convert text to audio
                with st.spinner("Converting text to speech..."):
                    combined_audio = tts_client.convert_text_to_audio_data(text_input.strip(), selected_voice)

                if not combined_audio:
                    st.error("Failed to generate audio")
                    return

                st.success("✅ Audio conversion completed!")

                # Store combined audio in session state
                st.session_state.combined_audio = combined_audio

            except Exception as e:
                st.error(f"❌ TTS conversion failed: {str(e)}")
    
    with col2:
        st.header("Audio Player")
        
        if 'combined_audio' in st.session_state and st.session_state.combined_audio:
            combined_audio = st.session_state.combined_audio
            
            # Audio info panel
            with st.container():
                col_info1, col_info2 = st.columns(2)
                with col_info1:
                    audio_size_mb = len(combined_audio) / (1024 * 1024)
                    st.metric("📊 Audio Size", f"{audio_size_mb:.2f} MB")
                with col_info2:
                    st.metric("🎵 Voice", voice_options.get(selected_voice, selected_voice).split(' - ')[0])
            
            st.markdown("**🎵 Your Audio is Ready!**")
            
            # Main audio player
            st.audio(
                combined_audio, 
                format=f'audio/{audio_format}',
                start_time=0,
                autoplay=auto_play,
                loop=False
            )
            
            # Additional audio information
            show_audio_info = st.checkbox("📊 Show detailed audio info", help="Display technical audio information")
            
            if show_audio_info:
                st.info(f"📊 Format: {audio_format.upper()} | Voice: {selected_voice} | Size: {audio_size_kb:.1f} KB")
            
            # Download section
            st.markdown("---")
            st.markdown("**💾 Download Audio**")
            
            col_download1, col_download2 = st.columns(2)
            
            with col_download1:
                st.download_button(
                    label="⬇️ Download Audio",
                    data=combined_audio,
                    file_name=f"podcast_{selected_voice}.{audio_format}",
                    mime=f"audio/{audio_format}",
                    use_container_width=True,
                    help="Download the complete audio file"
                )
            
            with col_download2:
                # Create a base64 encoded version for sharing
                audio_b64 = base64.b64encode(combined_audio).decode()
                audio_size_mb = len(combined_audio) / (1024 * 1024)
                st.write(f"📋 File size: {audio_size_mb:.2f} MB")
            
            # Playback tips
            with st.expander("� Playback Tips", expanded=False):
                st.markdown("""
                **🎵 Audio Playback:**
                - Use your browser's built-in controls for play/pause/seek
                - Right-click the audio player for additional options
                - The audio will play continuously without interruption
                - Compatible with all modern browsers and mobile devices
                
                **💾 Download Options:**
                - Click "Download Audio" to save the file locally
                - The downloaded file works with any audio player
                - Perfect for offline listening or sharing
                """)
        else:
            st.info("👆 Convert some text to see the audio player")
            st.markdown("""
            **🎵 Audio Player Features:**
            - 🎤 6 different voice styles to choose from
            - 🎵 Seamless audio playback without interruptions
            - 📊 Multiple audio format support (MP3, WAV, OGG)
            - 💾 Easy download for offline listening
            - � Mobile-optimized player controls
            - 🔊 Optional auto-play functionality
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
        - ✅ **Smart Text Processing**: Automatically handles long texts with intelligent processing
        - ✅ **Parallel Processing**: Faster generation with multi-threaded conversion
        - ✅ **Seamless Audio**: Creates continuous, uninterrupted audio playback
        - ✅ **Mobile-Optimized**: Responsive design works perfectly on phones
        - ✅ **Multiple Audio Formats**: Choose between MP3, WAV, and OGG formats
        - ✅ **Auto-Play Option**: Automatically start playing audio after conversion
        - ✅ **Secure Credentials**: API keys are completely hidden and secure
        - ✅ **Progress Tracking**: Real-time feedback during audio generation
        - ✅ **Easy Downloads**: Save complete audio files with one click
        
        ### 🎛️ Audio Controls
        - **Auto-Play**: Enable to automatically start playing audio after conversion
        - **Format Selection**: Choose the best audio format for your needs
        - **Browser Controls**: Use your browser's native audio controls for full playback control
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
        - **Smart Processing**: Texts are automatically processed in optimal segments for best quality
        - **Parallel Generation**: Multiple parts are generated simultaneously for faster results
        - **Seamless Combining**: Audio parts are seamlessly merged into continuous speech
        - **Memory Efficient**: Audio data is streamed efficiently without excessive memory usage
        
        ### 💡 Pro Tips
        - **Long Documents**: The app automatically handles long texts - just paste and convert!
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
        st.markdown("**🎵 Podcast Maker 🎧**")
        st.markdown("Built with ❤️ using Streamlit")
    
    with col_footer2:
        st.markdown("**🔗 Powered By**")
        st.markdown("Azure OpenAI TTS API")
    
    with col_footer3:
        st.markdown("**🔗 Github**")
        st.markdown("[View the Repository](https://github.com/EfeSenerr/podcast-maker-tts)")
if __name__ == "__main__":
    main()
