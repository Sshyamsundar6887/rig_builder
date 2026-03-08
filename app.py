"""
RIG-Builder — Main Flask Application
Generates personalized PC builds using AI and real-time pricing.
"""

import os
import json
import re
from datetime import datetime

from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

load_dotenv()

# ── Flask App Setup ─────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key-change-me")

basedir = os.path.abspath(os.path.dirname(__file__))

# Database: Use DATABASE_URL env var for production (PostgreSQL), fallback to SQLite for dev
database_url = os.getenv("DATABASE_URL", f"sqlite:///{os.path.join(basedir, 'instance', 'rig_builder.db')}")
# Fix Heroku/Render postgres:// -> postgresql://
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ── Flask-Login Setup ───────────────────────────────────────────────────
login_manager = LoginManager(app)
login_manager.login_view = "index"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ── Database Models ─────────────────────────────────────────────────────

class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    builds = db.relationship("Build", backref="user", lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Build(db.Model):
    __tablename__ = "builds"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    name = db.Column(db.String(200), default="My Build")
    budget = db.Column(db.Float)
    use_case = db.Column(db.String(100))
    performance_tier = db.Column(db.String(50))
    ai_summary = db.Column(db.Text)
    components_json = db.Column(db.Text)
    total_price = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "budget": self.budget,
            "use_case": self.use_case,
            "performance_tier": self.performance_tier,
            "ai_summary": self.ai_summary,
            "components": json.loads(self.components_json) if self.components_json else [],
            "total_price": self.total_price,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ── AI Engine ───────────────────────────────────────────────────────────

def _build_prompt(budget, use_case, performance_tier):
    """Create a structured prompt for the AI model."""
    return f"""You are a professional PC hardware expert. Generate a complete PC build recommendation.

REQUIREMENTS:
- Budget: ₹{budget} INR (Indian Rupees)
- Primary Use: {use_case}
- Performance Tier: {performance_tier}

RESPOND WITH ONLY a valid JSON object (no markdown, no code fences, no extra text).
The JSON must have this exact structure:
{{
  "summary": "A 2-3 sentence overview of this build and why these parts were chosen.",
  "components": [
    {{
      "category": "CPU",
      "name": "Full product name",
      "brand": "Brand name",
      "model": "Model number",
      "estimated_price": 299.99,
      "rationale": "Why this component was selected for this specific build."
    }},
    {{
      "category": "GPU",
      "name": "Full product name",
      "brand": "Brand name",
      "model": "Model number",
      "estimated_price": 499.99,
      "rationale": "Why this component was selected."
    }},
    {{
      "category": "Motherboard",
      "name": "Full product name",
      "brand": "Brand name",
      "model": "Model number",
      "estimated_price": 179.99,
      "rationale": "Why this component was selected."
    }},
    {{
      "category": "RAM",
      "name": "Full product name",
      "brand": "Brand name",
      "model": "Model number",
      "estimated_price": 79.99,
      "rationale": "Why this component was selected."
    }},
    {{
      "category": "Storage",
      "name": "Full product name",
      "brand": "Brand name",
      "model": "Model number",
      "estimated_price": 89.99,
      "rationale": "Why this component was selected."
    }},
    {{
      "category": "PSU",
      "name": "Full product name",
      "brand": "Brand name",
      "model": "Model number",
      "estimated_price": 99.99,
      "rationale": "Why this component was selected."
    }},
    {{
      "category": "Case",
      "name": "Full product name",
      "brand": "Brand name",
      "model": "Model number",
      "estimated_price": 79.99,
      "rationale": "Why this component was selected."
    }},
    {{
      "category": "Cooler",
      "name": "Full product name",
      "brand": "Brand name",
      "model": "Model number",
      "estimated_price": 49.99,
      "rationale": "Why this component was selected."
    }}
  ]
}}

IMPORTANT RULES:
1. Include exactly 8 components: CPU, GPU, Motherboard, RAM, Storage, PSU, Case, Cooler.
2. All components MUST be real, currently available products.
3. Components must be compatible with each other (matching socket, form factor, power budget).
4. Total estimated price should be close to but not exceed the budget of ₹{budget} INR.
5. Use real Indian market prices in INR — do not invent prices.
6. Return ONLY the JSON object. No additional text, comments, or formatting."""


def _extract_json(text):
    """Extract JSON from AI response, handling markdown code fences."""
    # Remove markdown code fences if present
    text = re.sub(r"```json\s*", "", text)
    text = re.sub(r"```\s*", "", text)
    text = text.strip()

    # Try to find JSON object in the text
    brace_start = text.find("{")
    brace_end = text.rfind("}") + 1
    if brace_start != -1 and brace_end > brace_start:
        try:
            return json.loads(text[brace_start:brace_end])
        except json.JSONDecodeError:
            pass

    # Last resort: try the whole text
    return json.loads(text)


def generate_with_gemini(prompt):
    """Call Google Gemini API."""
    import google.generativeai as genai

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.0-flash")

    response = model.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(
            temperature=0.7,
            max_output_tokens=2000,
        ),
    )
    return _extract_json(response.text)


def generate_with_groq(prompt):
    """Call Groq API with Llama 3."""
    from groq import Groq

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return None

    client = Groq(api_key=api_key)
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "You are a PC hardware expert. Respond only with valid JSON."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
        max_tokens=2000,
    )
    return _extract_json(response.choices[0].message.content)


def generate_build_ai(budget, use_case, performance_tier):
    """
    Generate a PC build using AI. Tries Gemini first, then Groq.
    Returns parsed JSON dict with 'summary' and 'components'.
    """
    prompt = _build_prompt(budget, use_case, performance_tier)

    # Try Gemini first
    try:
        result = generate_with_gemini(prompt)
        if result:
            return result
    except Exception as e:
        print(f"[AI] Gemini failed: {e}")

    # Fallback to Groq
    try:
        result = generate_with_groq(prompt)
        if result:
            return result
    except Exception as e:
        print(f"[AI] Groq failed: {e}")

    return None


# ── PDF Generator ───────────────────────────────────────────────────────

def generate_pdf(build_data):
    """Generate a PDF summary of a build. Returns the file path."""
    from fpdf import FPDF

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Title
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(0, 200, 255)
    pdf.cell(0, 15, "RIG-Builder", new_x="LMARGIN", new_y="NEXT", align="C")

    pdf.set_font("Helvetica", "", 12)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 8, "PC Build Summary", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(5)

    # Build info
    pdf.set_draw_color(0, 200, 255)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)

    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(50, 50, 50)
    pdf.cell(0, 7, f"Build Name: {build_data.get('name', 'My Build')}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 7, f"Budget: Rs.{build_data.get('budget', 0):,.2f}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 7, f"Use Case: {build_data.get('use_case', 'N/A')}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 7, f"Performance Tier: {build_data.get('performance_tier', 'N/A')}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 7, f"Total Estimated Price: Rs.{build_data.get('total_price', 0):,.2f}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    # AI Summary
    summary = build_data.get("ai_summary", "")
    if summary:
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(0, 150, 200)
        pdf.cell(0, 8, "AI Build Summary", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(60, 60, 60)
        pdf.multi_cell(0, 6, summary)
        pdf.ln(3)

    # Components table
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(0, 150, 200)
    pdf.cell(0, 10, "Components", new_x="LMARGIN", new_y="NEXT")

    components = build_data.get("components", [])
    if components:
        # Table header
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_fill_color(0, 180, 230)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(30, 8, "Category", border=1, fill=True)
        pdf.cell(75, 8, "Component", border=1, fill=True)
        pdf.cell(30, 8, "Brand", border=1, fill=True)
        pdf.cell(25, 8, "Price", border=1, fill=True, align="R")
        pdf.cell(30, 8, "Retailer", border=1, fill=True)
        pdf.ln()

        # Table rows
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(50, 50, 50)
        for i, comp in enumerate(components):
            fill = i % 2 == 0
            if fill:
                pdf.set_fill_color(240, 248, 255)
            else:
                pdf.set_fill_color(255, 255, 255)

            name = comp.get("name", "N/A")[:40]
            price = comp.get("estimated_price", 0)
            best_price_info = comp.get("prices", [])
            retailer = "Est."
            if best_price_info:
                best = min(best_price_info, key=lambda p: p.get("price", 9999))
                price = best.get("price", price)
                retailer = best.get("retailer", "Est.")

            pdf.cell(30, 7, comp.get("category", ""), border=1, fill=fill)
            pdf.cell(75, 7, name, border=1, fill=fill)
            pdf.cell(30, 7, comp.get("brand", ""), border=1, fill=fill)
            pdf.cell(25, 7, f"Rs.{price:,.0f}", border=1, fill=fill, align="R")
            pdf.cell(30, 7, retailer, border=1, fill=fill)
            pdf.ln()

        # Total row
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_fill_color(0, 180, 230)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(135, 8, "TOTAL", border=1, fill=True, align="R")
        pdf.cell(25, 8, f"Rs.{build_data.get('total_price', 0):,.0f}", border=1, fill=True, align="R")
        pdf.cell(30, 8, "", border=1, fill=True)
        pdf.ln()

    # Component rationales
    pdf.ln(5)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(0, 150, 200)
    pdf.cell(0, 10, "Why These Parts?", new_x="LMARGIN", new_y="NEXT")

    for comp in components:
        rationale = comp.get("rationale", "")
        if rationale:
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_text_color(0, 120, 180)
            pdf.cell(0, 6, f"{comp.get('category', '')}: {comp.get('name', '')}", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(80, 80, 80)
            pdf.multi_cell(0, 5, rationale)
            pdf.ln(2)

    # Footer
    pdf.ln(5)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 5, f"Generated by RIG-Builder on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", align="C")

    # Save file
    os.makedirs(os.path.join(basedir, "instance"), exist_ok=True)
    filepath = os.path.join(basedir, "instance", "build_export.pdf")
    pdf.output(filepath)
    return filepath


# ── PCPartPicker URL Builder ────────────────────────────────────────────

def build_pcpartpicker_url(components):
    """
    Build a PCPartPicker search URL for the components.
    Since PCPartPicker doesn't have a public API for pre-populating builds,
    we redirect to a search for the primary components.
    """
    parts = []
    for comp in components:
        name = comp.get("name", "")
        if name:
            parts.append(name)

    # Create a search URL with the build components
    search_query = " ".join(parts[:3])  # Use first 3 major components
    return f"https://pcpartpicker.com/search/?q={requests.utils.quote(search_query)}"


# ── Flask Routes ────────────────────────────────────────────────────────

@app.route("/")
def index():
    """Serve the main page."""
    return render_template("index.html")


# ── Auth Routes ─────────────────────────────────────────────────────────

@app.route("/auth/register", methods=["POST"])
def register():
    """Register a new user."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    username = data.get("username", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not username or not email or not password:
        return jsonify({"error": "All fields are required"}), 400

    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Username already taken"}), 409

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already registered"}), 409

    user = User(username=username, email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    login_user(user, remember=True)
    return jsonify({"message": "Account created!", "user": {"id": user.id, "username": user.username, "email": user.email}})


@app.route("/auth/login", methods=["POST"])
def login():
    """Log in a user."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    username = data.get("username", "").strip()
    password = data.get("password", "")

    user = User.query.filter(
        (User.username == username) | (User.email == username.lower())
    ).first()

    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid username or password"}), 401

    login_user(user, remember=True)
    return jsonify({"message": "Logged in!", "user": {"id": user.id, "username": user.username, "email": user.email}})


@app.route("/auth/logout", methods=["POST"])
def logout():
    """Log out the current user."""
    logout_user()
    return jsonify({"message": "Logged out"})


@app.route("/auth/me")
def auth_me():
    """Get current user info."""
    if current_user.is_authenticated:
        return jsonify({"authenticated": True, "user": {"id": current_user.id, "username": current_user.username, "email": current_user.email}})
    return jsonify({"authenticated": False})


@app.route("/generate", methods=["POST"])
def generate():
    """Generate a PC build using AI and scrape prices."""
    import requests as req_lib  # avoid name collision

    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    budget = data.get("budget", 1000)
    use_case = data.get("use_case", "Gaming")
    performance_tier = data.get("performance_tier", "Mid-Range")

    # Step 1: Generate build with AI
    ai_result = generate_build_ai(budget, use_case, performance_tier)
    if not ai_result:
        return jsonify({"error": "AI service unavailable. Please check your API keys in .env"}), 503

    components = ai_result.get("components", [])
    summary = ai_result.get("summary", "")

    # Step 2: Scrape prices asynchronously
    try:
        from scraper import scrape_all_components
        price_data = scrape_all_components(components)

        # Merge price data into components
        for comp in components:
            comp_name = comp.get("name", "")
            comp["prices"] = price_data.get(comp_name, [])
    except Exception as e:
        print(f"[Scraper] Error: {e}")
        for comp in components:
            comp["prices"] = []

    # Calculate total price (use scraped prices when available, otherwise estimated)
    total = 0
    for comp in components:
        prices = comp.get("prices", [])
        if prices:
            best = min(prices, key=lambda p: p.get("price", 9999))
            total += best.get("price", comp.get("estimated_price", 0))
        else:
            total += comp.get("estimated_price", 0)

    return jsonify({
        "summary": summary,
        "components": components,
        "total_price": round(total, 2),
        "budget": budget,
        "use_case": use_case,
        "performance_tier": performance_tier,
    })


@app.route("/save", methods=["POST"])
def save():
    """Save a build to the database."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    build = Build(
        user_id=current_user.id if current_user.is_authenticated else None,
        name=data.get("name", f"{data.get('use_case', 'Custom')} Build"),
        budget=data.get("budget", 0),
        use_case=data.get("use_case", ""),
        performance_tier=data.get("performance_tier", ""),
        ai_summary=data.get("summary", ""),
        components_json=json.dumps(data.get("components", [])),
        total_price=data.get("total_price", 0),
    )
    db.session.add(build)
    db.session.commit()

    return jsonify({"message": "Build saved!", "id": build.id})


@app.route("/history")
def history():
    """Get saved builds for the current user."""
    if current_user.is_authenticated:
        builds = Build.query.filter_by(user_id=current_user.id).order_by(Build.created_at.desc()).all()
    else:
        builds = []
    return jsonify([b.to_dict() for b in builds])


@app.route("/export")
def export():
    """Export a build as PDF."""
    build_id = request.args.get("id")

    if build_id:
        build = Build.query.get(build_id)
        if not build:
            return jsonify({"error": "Build not found"}), 404
        build_data = build.to_dict()
    else:
        # Export from posted data (unsaved build)
        return jsonify({"error": "No build ID provided"}), 400

    filepath = generate_pdf(build_data)
    return send_file(filepath, as_attachment=True, download_name=f"RIG_Build_{build_id}.pdf")


@app.route("/export-current", methods=["POST"])
def export_current():
    """Export the current (unsaved) build as PDF."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    filepath = generate_pdf(data)
    return send_file(filepath, as_attachment=True, download_name="RIG_Build.pdf")


@app.route("/pcpartpicker/<int:build_id>")
def pcpartpicker(build_id):
    """Redirect to PCPartPicker with build components."""
    build = Build.query.get(build_id)
    if not build:
        return jsonify({"error": "Build not found"}), 404

    components = json.loads(build.components_json) if build.components_json else []
    url = build_pcpartpicker_url(components)
    return redirect(url)


@app.route("/delete/<int:build_id>", methods=["DELETE"])
def delete_build(build_id):
    """Delete a saved build."""
    build = Build.query.get(build_id)
    if not build:
        return jsonify({"error": "Build not found"}), 404

    db.session.delete(build)
    db.session.commit()
    return jsonify({"message": "Build deleted"})


# ── Chat AI Engine ──────────────────────────────────────────────────────

def _chat_prompt(user_message, chat_history=None):
    """Build a chat prompt that extracts requirements from natural language."""
    history_text = ""
    if chat_history:
        for msg in chat_history[-6:]:  # Keep last 6 messages for context
            role = "User" if msg["role"] == "user" else "Assistant"
            history_text += f"{role}: {msg['content']}\n"

    return f"""You are RIG Assistant, a friendly and knowledgeable PC hardware expert chatbot.

The user is describing what they need from a PC in natural language. Your job is to:
1. Understand their requirements (games, software, resolution, FPS targets, budget, etc.)
2. If you have enough information, generate a complete PC build.
3. If important details are missing (especially budget), ask a brief follow-up question.

CONVERSATION HISTORY:
{history_text}

CURRENT USER MESSAGE: {user_message}

IMPORTANT: All prices must be in Indian Rupees (INR). Use real Indian market prices.

RESPOND WITH ONLY a valid JSON object (no markdown, no code fences):

If you need more information:
{{
  "type": "question",
  "message": "Your friendly follow-up question here"
}}

If you have enough info to build:
{{
  "type": "build",
  "message": "A friendly 1-2 sentence response about what you're building for them.",
  "budget": 1500,
  "use_case": "Extracted use case description",
  "performance_tier": "Mid-Range",
  "summary": "A 2-3 sentence overview of this build.",
  "components": [
    {{
      "category": "CPU",
      "name": "Full product name",
      "brand": "Brand name",
      "model": "Model number",
      "estimated_price": 299.99,
      "rationale": "Why this was chosen for their specific needs."
    }},
    {{
      "category": "GPU",
      "name": "Full product name",
      "brand": "Brand name",
      "model": "Model number",
      "estimated_price": 499.99,
      "rationale": "Why this was chosen."
    }},
    {{
      "category": "Motherboard",
      "name": "Full product name",
      "brand": "Brand name",
      "model": "Model number",
      "estimated_price": 179.99,
      "rationale": "Why this was chosen."
    }},
    {{
      "category": "RAM",
      "name": "Full product name",
      "brand": "Brand name",
      "model": "Model number",
      "estimated_price": 79.99,
      "rationale": "Why this was chosen."
    }},
    {{
      "category": "Storage",
      "name": "Full product name",
      "brand": "Brand name",
      "model": "Model number",
      "estimated_price": 89.99,
      "rationale": "Why this was chosen."
    }},
    {{
      "category": "PSU",
      "name": "Full product name",
      "brand": "Brand name",
      "model": "Model number",
      "estimated_price": 99.99,
      "rationale": "Why this was chosen."
    }},
    {{
      "category": "Case",
      "name": "Full product name",
      "brand": "Brand name",
      "model": "Model number",
      "estimated_price": 79.99,
      "rationale": "Why this was chosen."
    }},
    {{
      "category": "Cooler",
      "name": "Full product name",
      "brand": "Brand name",
      "model": "Model number",
      "estimated_price": 49.99,
      "rationale": "Why this was chosen."
    }}
  ]
}}

RULES:
- If user mentions a game, research what hardware that game needs at their target settings.
- If no budget is mentioned, infer a reasonable one or ask.
- All 8 component categories are required for a build: CPU, GPU, Motherboard, RAM, Storage, PSU, Case, Cooler.
- All components must be real, currently available products with real prices.
- Components must be compatible (socket, form factor, power).
- Return ONLY JSON. No extra text."""


def generate_chat_ai(user_message, chat_history=None):
    """Process a chat message through AI. Returns parsed JSON."""
    prompt = _chat_prompt(user_message, chat_history)

    # Try Gemini first
    try:
        result = generate_with_gemini(prompt)
        if result:
            return result
    except Exception as e:
        print(f"[Chat AI] Gemini failed: {e}")

    # Fallback to Groq
    try:
        result = generate_with_groq(prompt)
        if result:
            return result
    except Exception as e:
        print(f"[Chat AI] Groq failed: {e}")

    return None


@app.route("/chat", methods=["POST"])
def chat():
    """Handle chatbot messages — parse natural language into builds."""
    data = request.get_json()
    if not data or not data.get("message"):
        return jsonify({"error": "No message provided"}), 400

    user_message = data["message"]
    chat_history = data.get("history", [])

    ai_result = generate_chat_ai(user_message, chat_history)
    if not ai_result:
        return jsonify({
            "type": "question",
            "message": "I'm having trouble connecting to the AI service right now. Could you try again in a moment?"
        })

    # If it's a build response, scrape prices
    if ai_result.get("type") == "build":
        components = ai_result.get("components", [])
        try:
            from scraper import scrape_all_components
            price_data = scrape_all_components(components)
            for comp in components:
                comp["prices"] = price_data.get(comp.get("name", ""), [])
        except Exception as e:
            print(f"[Chat Scraper] Error: {e}")
            for comp in components:
                comp["prices"] = []

        # Calculate total price
        total = 0
        for comp in components:
            prices = comp.get("prices", [])
            if prices:
                best = min(prices, key=lambda p: p.get("price", 9999))
                total += best.get("price", comp.get("estimated_price", 0))
            else:
                total += comp.get("estimated_price", 0)

        ai_result["total_price"] = round(total, 2)

    return jsonify(ai_result)


# ── App Startup ─────────────────────────────────────────────────────────

with app.app_context():
    os.makedirs(os.path.join(basedir, "instance"), exist_ok=True)
    db.create_all()

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  RIG-Builder is running!")
    print("  Open http://127.0.0.1:5000 in your browser")
    print("=" * 60 + "\n")
    app.run(debug=True, port=5000)
