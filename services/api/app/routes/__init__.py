from app.routes.loads import router as loads_router
from app.routes.fleet import router as fleet_router
from app.routes.tracking import router as tracking_router
from app.routes.webhooks import router as webhooks_router
from app.routes.ocr import router as ocr_router
from app.routes.dispatch import router as dispatch_router

routers = [
    loads_router,
    fleet_router,
    tracking_router,
    webhooks_router,
    ocr_router,
    dispatch_router
]
