# Azure TTS Streamlit App

A web-based Text-to-Speech application using Azure OpenAI's TTS API, built with Streamlit for easy deployment and mobile access.

## 🌟 Features

- **📱 Mobile-Friendly**: Works perfectly on phones and tablets
- **🎵 Multiple Voices**: Choose from 6 different voices (alloy, echo, fable, onyx, nova, shimmer)
- **⚡ Parallel Processing**: Fast audio generation with automatic text chunking
- **🎧 Audio Player**: Built-in player with chunk navigation
- **💾 Download Support**: Download individual chunks or complete audio
- **🆓 Free Deployment**: Deploy for free on Streamlit Cloud

## 🚀 Live Demo

🔗 **[Try it here](https://your-app-name.streamlit.app)** (link will be available after deployment)

## 📱 Mobile Access

This app is optimized for mobile devices! Access it from your phone's browser for on-the-go text-to-speech conversion.

## 🛠️ Local Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/azure-tts-streamlit.git
   cd azure-tts-streamlit
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements_streamlit.txt
   ```

3. **Run the app:**
   ```bash
   streamlit run streamlit_tts_app.py
   ```

4. **Open your browser** to `http://localhost:8501`

## ⚙️ Configuration

1. Enter your Azure OpenAI endpoint URL
2. Add your API key
3. Select your preferred voice
4. Start converting text to speech!

## 📋 Requirements

- Python 3.7+
- Azure OpenAI TTS API access
- Streamlit
- Requests

## 🎯 How It Works

1. **Text Chunking**: Long texts are automatically split into chunks (≤4000 characters)
2. **Parallel Processing**: Multiple API calls process chunks simultaneously
3. **Sequential Playback**: Audio chunks play in order for natural speech flow
4. **Mobile Optimization**: Responsive design works on all devices

## 📁 Project Structure

```
azure-tts-streamlit/
├── streamlit_tts_app.py          # Main Streamlit application
├── requirements_streamlit.txt     # Python dependencies
├── README.md                     # This file
└── web_tts_app.py               # Alternative Flask version
```

## 🆓 Free Deployment Options

### Streamlit Cloud (Recommended)
1. Push to GitHub
2. Connect to Streamlit Cloud
3. Deploy instantly - no cost!

### Other Options
- Heroku (free tier)
- Railway (free tier)
- Render (free tier)

## 🔐 Security Note

For production use, consider using environment variables or Streamlit secrets for API credentials instead of hardcoding them.

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

## 🤝 Contributing

Contributions, issues, and feature requests are welcome! Feel free to check the [issues page](https://github.com/your-username/azure-tts-streamlit/issues).

## ⭐ Support

If this project helps you, please give it a ⭐ on GitHub!
