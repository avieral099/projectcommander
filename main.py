import requests
response = requests.get("https://api.github.com")
data = response.json()
print(data["current_user_url"])
print(data["authorizations_url"])
print(data["repository_url"])
for key in data:
    print(key)
    


