# Import Required Libraries

from fyers_apiv3 import fyersModel
from config import APP_ID


# Read Access Token

with open("access_token.txt", "r") as file:
    access_token = file.read().strip()


# Create FYERS Client

fyers = fyersModel.FyersModel(
    client_id=APP_ID,
    token=access_token,
    is_async=False,
    log_path=""
)