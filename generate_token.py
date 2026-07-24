# Import FYERS SDK
from fyers_apiv3 import fyersModel

# Import App Credentials
from config import APP_ID, SECRET_KEY, REDIRECT_URI

# Take Auth Code from Terminal
AUTH_CODE = input("Paste Auth Code: ").strip()

# Create Session
session = fyersModel.SessionModel(
    client_id=APP_ID,
    secret_key=SECRET_KEY,
    redirect_uri=REDIRECT_URI,
    response_type="code",
    grant_type="authorization_code"
)

# Set Auth Code
session.set_token(AUTH_CODE)

# Generate Access Token
response = session.generate_token()

# Print Response
print(response)
access_token = response["access_token"]

with open("access_token.txt", "w") as file:
    file.write(access_token)

print("Token Saved Successfully")
