import aiohttp
import os
from dotenv import load_dotenv

load_dotenv()

API_BASE_URL = os.getenv('API_BASE_URL', 'http://localhost:8000')

class APIClient:
    def __init__(self):
        self._session = None
    
    async def _get_session(self):
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session
    
    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def get_loads(self, status=None):
        session = await self._get_session()
        params = {'status': status} if status else {}
        async with session.get(f'{API_BASE_URL}/api/loads', params=params) as resp:
            return await resp.json()
    
    async def create_load(self, data):
        session = await self._get_session()
        async with session.post(f'{API_BASE_URL}/api/loads', json=data) as resp:
            return await resp.json()
    
    async def update_load_status(self, load_id, message, user_id):
        session = await self._get_session()
        async with session.post(f'{API_BASE_URL}/api/webhooks/discord/status-update', json={
            'message': message, 'user_id': user_id, 'load_id': load_id
        }) as resp:
            return await resp.json()
    
    async def submit_document(self, file_url, filename, user_id, message=''):
        session = await self._get_session()
        async with session.post(f'{API_BASE_URL}/api/webhooks/discord/document', json={
            'file_url': file_url, 'filename': filename, 'user_id': user_id, 'message': message
        }) as resp:
            return await resp.json()
    
    async def submit_onboarding(self, data):
        session = await self._get_session()
        async with session.post(f'{API_BASE_URL}/api/webhooks/discord/onboard', json=data) as resp:
            return await resp.json()
    
    async def track_vehicle(self, unit_id):
        session = await self._get_session()
        async with session.get(f'{API_BASE_URL}/api/track/{unit_id}') as resp:
            return await resp.json()
    
    async def auto_dispatch(self):
        session = await self._get_session()
        async with session.post(f'{API_BASE_URL}/api/dispatch/auto') as resp:
            return await resp.json()
    
    async def predict_profit(self, origin, destination, rate):
        session = await self._get_session()
        async with session.post(f'{API_BASE_URL}/api/dispatch/predict', json={
            'origin': origin, 'destination': destination, 'rate': rate
        }) as resp:
            return await resp.json()
