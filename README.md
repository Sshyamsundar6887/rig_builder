<div align="center">
  <h1 style="font-size: 3rem; margin-bottom: 0;">🖥️</h1>
  <h1>🖥️ RIG-Builder</h1>
  <p><strong>Your Personal AI-Powered PC Building Assistant</strong></p>

  [![Python](https://img.shields.io/badge/Python-3.x-blue.svg?style=for-the-badge&logo=python)](https://www.python.org/)
  [![Flask](https://img.shields.io/badge/Flask-Web%20App-black.svg?style=for-the-badge&logo=flask)](https://flask.palletsprojects.com/)
  [![Google Gemini](https://img.shields.io/badge/AI-Google%20Gemini-orange.svg?style=for-the-badge&logo=googlegemini)](https://ai.google.dev/)
  [![Groq](https://img.shields.io/badge/AI-Groq%20Llama%203-red.svg?style=for-the-badge)](https://groq.com/)
</div>

<br />

## 📖 Overview

**RIG-Builder** is a powerful, intelligent web application that takes the guesswork out of building a custom PC. By leveraging state-of-the-art AI models (Google Gemini and Groq) alongside real-time web scraping, RIG-Builder generates highly optimized, compatible, and budget-friendly PC part lists tailored to your exact needs.

Whether you're building a blazing-fast gaming rig, a heavy-duty workstation, or a budget office PC, RIG-Builder does the heavy lifting for you!

<br />

## ✨ Features

- **🤖 AI-Powered PC Generation**: Provide your budget, use case (e.g., Gaming, Video Editing), and performance tier, and let the AI instantly recommend a complete 8-component build.
- **💬 Natural Language Chatbot**: Describe what you need in plain English via the built-in AI assistant, and it will interpret your requirements to suggest the perfect build.
- **💰 Real-Time Price Scraping**: Always get the most accurate estimated costs with automated web scraping for the latest component prices (in INR).
- **🔒 User Accounts & Build History**: Secure registration and login system. Save your favorite builds to your profile and access them anytime.
- **📄 PDF Export**: Generate a beautifully formatted, detailed PDF summary of your build—complete with parts, prices, and the AI's rationale for picking them.
- **🔗 PCPartPicker Integration**: One-click redirect to jumpstart your build on PCPartPicker to double-check compatibility and explore alternatives.

<br />

## 🛠️ Tech Stack

### Backend
- **Framework**: Flask (`flask`, `flask-login`, `flask-sqlalchemy`)
- **Database**: PostgreSQL (Production) / SQLite (Development)
- **Web Scraping**: `requests`, `beautifulsoup4`

### Frontend
- **Templates**: HTML5, Vanilla CSS
- **Interactions**: Vanilla JavaScript

### AI & Integrations
- **Primary AI Engine**: Google Gemini API (`google-generativeai`)
- **Fallback AI Engine**: Groq API/Llama 3 (`groq`)
- **PDF Generation**: `fpdf2`

<br />

## 🚀 Getting Started

Follow these instructions to get a copy of the project up and running on your local machine.

### Prerequisites

- Python 3.8+ installed
- API Keys for **Google Gemini** and/or **Groq**

### Installation Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/rig-builder.git
   cd rig-builder
   ```

2. **Create and Activate a Virtual Environment**
   ```bash
   python -m venv venv
   # Windows:
   venv\Scripts\activate
   # macOS/Linux:
   source venv/bin/activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set Up Environment Variables**
   Create a `.env` file in the root directory and add the following:
   ```env
   # Required AI API Keys
   GEMINI_API_KEY=your_gemini_api_key_here
   GROQ_API_KEY=your_groq_api_key_here
   
   # App Config Secrets
   FLASK_SECRET_KEY=your_super_secret_key
   
   # Database (Optional: defaults to local SQLite if omitted)
   DATABASE_URL=sqlite:///instance/rig_builder.db
   ```

5. **Run the Application**
   ```bash
   python app.py
   ```
   *The server will start at `http://127.0.0.1:5000/`. Open this URL in your browser!*

<br />

## 📸 Screenshots (Coming Soon)
*(Tip: Add your application screenshots here once deployed!)*

<br />


---

<div align="center">
  <i>Built with ❤️ for PC Builders everywhere.</i>
</div>
