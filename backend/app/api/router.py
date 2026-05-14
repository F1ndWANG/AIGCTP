from fastapi import APIRouter

from app.api import auth, chat, commerce, diet, feedback, recommendation, restaurant, route, runtime, share, travel, users


api_router = APIRouter()
API_ROUTERS = (
    auth.router,
    users.router,
    travel.router,
    chat.router,
    route.router,
    diet.router,
    commerce.router,
    feedback.router,
    restaurant.router,
    runtime.router,
    recommendation.router,
    share.router,
)

for router in API_ROUTERS:
    api_router.include_router(router)
