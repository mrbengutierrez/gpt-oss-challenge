import requests
from bs4 import BeautifulSoup

BASE_URL = "https://pharmabeaver.fly.dev"


def login(username: str, password: str) -> requests.Session | None:
    """
    Try to log in and return an authenticated session if successful.
    Otherwise return None.
    """
    session = requests.Session()

    # Step 1: grab CSRF token
    login_page = session.get(f"{BASE_URL}/login")
    soup = BeautifulSoup(login_page.text, "html.parser")
    csrf_input = soup.find("input", {"name": "csrf_token"})
    if not csrf_input:
        return None
    csrf_token = csrf_input["value"]

    # Step 2: post credentials
    payload = {
        "csrf_token": csrf_token,
        "username": username,
        "password": password,
    }
    resp = session.post(f"{BASE_URL}/login", data=payload)

    # Step 3: check login success
    if "Logout" in resp.text or resp.url != f"{BASE_URL}/login":
        return session  # success
    return None


# Example usage
if __name__ == "__main__":
    session = login("alice", "password123")
    if session:
        print("✅ Login success")
        products_page = session.get(f"{BASE_URL}/products")
        print(products_page.text[:500])
    else:
        print("❌ Login failed")
    session = login("alice", "asfsdf")
    if session:
        print("✅ Login success")
        products_page = session.get(f"{BASE_URL}/products")
        print(products_page.text[:500])
    else:
        print("❌ Login failed")