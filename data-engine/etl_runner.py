import os, requests, pandas as pd, joblib
from sqlalchemy import create_engine, text
from datetime import datetime
import xgboost as xgb
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
DATABASE_URL = SUPABASE_URL.replace("https://", f"https://{SUPABASE_KEY}@") + "/postgres"
engine = create_engine(DATABASE_URL)

def run():
    logger.info("🚀 CEIP Professional Data Factory")
    with engine.connect() as conn:
        # 1. GDP World Bank
        logger.info("🌍 Fetching GDP...")
        url = "http://api.worldbank.org/v2/country/CMR;GAB;COG;TCD;CAF;GNQ/indicator/NY.GDP.MKTP.KD.ZG?format=json"
        resp = requests.get(url).json()
        if len(resp) > 1:
            for entry in resp[1]:
                c, d, v = entry['country']['id'], entry['date'], entry['value']
                if v and int(d) >= 2010:
                    conn.execute(text("""
                        INSERT INTO observations (indicator_code, country_code, observation_date, value, revision_number)
                        VALUES ('GDP', :cc, :d, :v, 1)
                        ON CONFLICT (indicator_code, country_code, observation_date, revision_number)
                        DO UPDATE SET value = EXCLUDED.value
                    """), {"cc": c, "d": f"{d}-01-01", "v": float(v)})
            conn.commit()

        # 2. CPI World Bank
        logger.info("🌍 Fetching CPI...")
        url_cpi = "http://api.worldbank.org/v2/country/CMR;GAB;COG;TCD;CAF;GNQ/indicator/FP.CPI.TOTL.ZG?format=json"
        resp_cpi = requests.get(url_cpi).json()
        if len(resp_cpi) > 1:
            for entry in resp_cpi[1]:
                c, d, v = entry['country']['id'], entry['date'], entry['value']
                if v and int(d) >= 2010:
                    conn.execute(text("""
                        INSERT INTO observations (indicator_code, country_code, observation_date, value, revision_number)
                        VALUES ('CPI', :cc, :d, :v, 1)
                        ON CONFLICT (indicator_code, country_code, observation_date, revision_number)
                        DO UPDATE SET value = EXCLUDED.value
                    """), {"cc": c, "d": f"{d}-01-01", "v": float(v)})
            conn.commit()
        logger.info("✅ Data updated.")

        # 3. IA Simple (Nowcast)
        logger.info("🧠 Training XGBoost...")
        df = pd.read_sql("""
            SELECT o.country_code, o.value as gdp, LAG(o.value,1) OVER (PARTITION BY o.country_code ORDER BY o.observation_date) as lag_gdp,
                   c.value as cpi
            FROM observations o LEFT JOIN observations c ON c.country_code=o.country_code AND c.observation_date=o.observation_date AND c.indicator_code='CPI'
            WHERE o.indicator_code='GDP' AND o.observation_date > '2010-01-01'
        """, engine).dropna()
        if len(df) > 10:
            X = df[['lag_gdp', 'cpi']]
            y = df['gdp']
            model = xgb.XGBRegressor(n_estimators=50, random_state=42)
            model.fit(X, y)
            for c in ['CMR', 'GAB', 'COG', 'TCD', 'CAF', 'GNQ']:
                last = df[df['country_code']==c].iloc[-1:] if not df[df['country_code']==c].empty else None
                if last is not None and len(last)>0:
                    pred = model.predict(last[['lag_gdp', 'cpi']].fillna(0))[0]
                    conn.execute(text("""
                        INSERT INTO predictions (country_code, indicator_code, prediction_date, value, model_version)
                        VALUES (:cc, 'GDP_NOWCAST', NOW(), :v, 'xgb_v1')
                    """), {"cc": c, "v": float(pred)})
                    logger.info(f"📈 Nowcast {c}: {round(pred,2)}%")
            conn.commit()

        # 4. Alertes
        logger.info("🔔 Checking alerts...")
        alerts = conn.execute(text("SELECT country_code, value FROM observations WHERE indicator_code='CPI' ORDER BY observation_date DESC LIMIT 1")).fetchall()
        for row in alerts:
            if row[1] > 7.0:
                conn.execute(text("""
                    INSERT INTO alerts (severity, indicator_code, country_code, message)
                    VALUES ('RED', 'CPI', :cc, :msg)
                """), {"cc": row[0], "msg": f"Inflation critique : {row[1]}%"})
                logger.warning(f"🚨 ALERTE RED: Inflation {row[1]}% au {row[0]}")
        conn.commit()
        logger.info("✅ Pipeline completed.")

if __name__ == "__main__":
    run()