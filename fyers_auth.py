# 1. Import FYERS SDK
from fyers_apiv3 import fyersModel

# 2. Import credentials
from config import APP_ID, SECRET_KEY, REDIRECT_URI

# 3. Create session
session = fyersModel.SessionModel(
    client_id=APP_ID,
    secret_key=SECRET_KEY,
    redirect_uri=REDIRECT_URI,
    response_type="code",
    grant_type="authorization_code"
)

# 4. Generate Login URL
auth_url = session.generate_authcode()

# 5. Print URL
print(auth_url)
