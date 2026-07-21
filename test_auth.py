from app.auth import UpstoxAuth

auth = UpstoxAuth()

print("Token Valid :", auth.is_valid())
print("Token       :", auth.get_token())
