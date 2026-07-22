import os, json
from fastapi import FastAPI, Depends, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import redis

# Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# Base de données
DATABASE_URL = SUPABASE_URL.replace("https://", f"https://{SUPABASE_KEY}@") + "/postgres"
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)

# Redis
r = redis.Redis.from_url(REDIS_URL, decode_responses=True)

app = FastAPI(title="CEIP Professional API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dépendance DB
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def root():
    return {"status": "CEIP API is running", "version": "1.0"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/api/v1/dashboard/{country_code}")
def get_dashboard(country_code: str, db: SessionLocal = Depends(get_db)):
    cache_key = f"dash_{country_code}"
    cached = r.get(cache_key)
    if cached:
        return json.loads(cached)

    # 1. Dernières valeurs
    gdp = db.execute(text("SELECT value FROM observations WHERE country_code=:cc AND indicator_code='GDP' ORDER BY observation_date DESC LIMIT 1"), {"cc": country_code}).scalar() or 0.0
    cpi = db.execute(text("SELECT value FROM observations WHERE country_code=:cc AND indicator_code='CPI' ORDER BY observation_date DESC LIMIT 1"), {"cc": country_code}).scalar() or 0.0
    debt = db.execute(text("SELECT value FROM observations WHERE country_code=:cc AND indicator_code='DEBT' ORDER BY observation_date DESC LIMIT 1"), {"cc": country_code}).scalar() or 0.0

    # 2. Historique (8 dernières années)
    history = db.execute(text("SELECT observation_date, value FROM observations WHERE country_code=:cc AND indicator_code='GDP' ORDER BY observation_date ASC"), {"cc": country_code}).fetchall()

    # 3. Score santé
    score = 50
    if gdp > 3.0: score += 20
    elif gdp > 1.0: score += 10
    if cpi < 5.0: score += 20
    elif cpi < 8.0: score += 10
    if debt < 60.0: score += 10
    score = min(100, score)

    data = {
        "country": country_code,
        "latest_gdp": round(gdp, 2),
        "latest_inflation": round(cpi, 2),
        "debt_ratio": round(debt, 2),
        "health_score": score,
        "history": [{"date": str(row[0]), "value": row[1]} for row in history]
    }

    r.setex(cache_key, 3600, json.dumps(data))
    return data

@app.get("/api/v1/reports/{country_code}")
def generate_report(country_code: str, db: SessionLocal = Depends(get_db)):
    import io
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    import matplotlib.pyplot as plt
    import matplotlib
    matplotlib.use('Agg')

    # Récupération des données pour le rapport
    history = db.execute(text("SELECT observation_date, value FROM observations WHERE country_code=:cc AND indicator_code='GDP' ORDER BY observation_date ASC"), {"cc": country_code}).fetchall()
    latest = db.execute(text("SELECT value FROM observations WHERE country_code=:cc AND indicator_code='GDP' ORDER BY observation_date DESC LIMIT 1"), {"cc": country_code}).scalar() or 0.0

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    # Titre
    title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=16, spaceAfter=12)
    story.append(Paragraph(f"📊 Rapport CEIP - {country_code}", title_style))
    story.append(Spacer(1, 12))

    # KPI
    story.append(Paragraph(f"<b>PIB Croissance (Dernier trimestre) :</b> {latest}%", styles['Normal']))
    story.append(Spacer(1, 12))

    # Graphique
    if history:
        dates = [str(row[0]) for row in history]
        values = [row[1] for row in history]
        fig, ax = plt.subplots(figsize=(6, 3))
        ax.plot(dates, values, marker='o', linestyle='-', color='#1a365d')
        ax.set_title('Évolution du PIB')
        ax.grid(True)
        plt.tight_layout()
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', dpi=100)
        plt.close()
        img_buffer.seek(0)
        img = Image(img_buffer, width=6*inch, height=3*inch)
        story.append(img)

    story.append(Spacer(1, 12))
    story.append(Paragraph("Généré automatiquement par CEIP - CEMAC Economic Intelligence Platform", styles['Normal']))
    doc.build(story)
    buffer.seek(0)
    
    return Response(content=buffer.read(), media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=CEIP_{country_code}.pdf"})