# Import FYERS SDK
from fyers_apiv3 import fyersModel

# Import Credentials
from config import APP_ID

with open("access_token.txt", "r") as file:
    ACCESS_TOKEN = file.read().strip()

# Create FYERS Object
fyers = fyersModel.FyersModel(
    client_id=APP_ID,
    token=ACCESS_TOKEN,
    is_async=False
)

# Fetch Profile
profile = fyers.get_profile()

# Print Response
print(profile)