from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import init_db, seed_data
from app.routes import routers

app = FastAPI(title="HAUL-E TMS API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    await init_db()
    await seed_data()

for router in routers:
    app.include_router(router)

from pydantic import BaseModel
import asyncio

class PredictionRequest(BaseModel):
    origin: str
    destination: str
    rate: str | float

@app.post("/api/predict")
async def legacy_predict_profit(req: PredictionRequest):
    await asyncio.sleep(1) # Simulate AI prediction
    try:
        if isinstance(req.rate, (int, float)):
            rate_num = float(req.rate)
        else:
            rate_num = float(req.rate.replace(',', '').replace('$', '')) if req.rate else 4000.0
    except ValueError:
        rate_num = 4000.0
    fuel = rate_num * 0.25
    driver = rate_num * 0.40
    tolls = rate_num * 0.05
    overhead = rate_num * 0.10
    profit = rate_num - (fuel + driver + tolls + overhead)
    
    return {
        "fuel": f"${fuel:.2f}",
        "driver": f"${driver:.2f}",
        "tolls": f"${tolls:.2f}",
        "overhead": f"${overhead:.2f}",
        "profit": f"${profit:.2f}",
        "margin": f"{(profit/rate_num)*100:.1f}%",
        "recommendation": "Accept Load" if profit > 500 else "Reject / Negotiate"
    }
