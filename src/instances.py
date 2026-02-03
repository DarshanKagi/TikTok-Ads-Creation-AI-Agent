from src.config import USE_REAL_API
from src.api_mock import MockTikTokAPI
from src.api_real import RealTikTokAPI
from src.agent import AdAgent

api_client = RealTikTokAPI() if USE_REAL_API else MockTikTokAPI()
agent = AdAgent(api_client)
