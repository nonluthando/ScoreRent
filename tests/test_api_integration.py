# ------------------------------------------------------------
# Unauthorized access
# ------------------------------------------------------------

def test_api_requires_authentication(client):
    response = client.get("/api/evaluations")
    assert response.status_code == 401


# ------------------------------------------------------------
# Signup + session + API access
# ------------------------------------------------------------

def test_signup_and_access_api(client):

    # Signup
    response = client.post("/signup", data={
        "email": "test@example.com",
        "password": "StrongPassword123"
    })

    assert response.status_code == 303

    # Access API (session cookie auto-handled)
    response = client.get("/api/evaluations")
    assert response.status_code == 200
    assert response.json()["evaluations"] == []


# ------------------------------------------------------------
# Create profile + evaluation flow
# ------------------------------------------------------------

def test_full_evaluation_flow(client):

    # Signup
    client.post("/signup", data={
        "email": "user@example.com",
        "password": "Password123"
    })

    # Create profile
    client.post("/profile", data={
        "renter_type": "worker",
        "monthly_income": 30000,
        "renter_docs": ["bank statement", "payslip"]
    })

    # Create evaluation
    client.post("/evaluate", data={
        "listing_name": "Test Listing",
        "rent": 8000,
        "deposit": 8000,
        "application_fee": 500,
        "area_demand": "MEDIUM",
        "required_documents": []
    })

    # Fetch via API
    response = client.get("/api/evaluations")
    data = response.json()

    assert response.status_code == 200
    assert data["total"] == 1
    assert len(data["evaluations"]) == 1
    assert data["evaluations"][0]["listing_name"] == "Test Listing"


# ------------------------------------------------------------
# Ownership enforcement
# ------------------------------------------------------------

def test_user_cannot_access_other_users_evaluation(client):

    # User 1
    client.post("/signup", data={
        "email": "user1@example.com",
        "password": "Password123"
    })

    client.post("/profile", data={
        "renter_type": "worker",
        "monthly_income": 30000,
        "renter_docs": ["bank statement", "payslip"]
    })

    client.post("/evaluate", data={
        "listing_name": "User1 Listing",
        "rent": 8000,
        "deposit": 8000,
        "application_fee": 0,
        "area_demand": "MEDIUM",
        "required_documents": []
    })

    response = client.get("/api/evaluations")
    eval_id = response.json()["evaluations"][0]["id"]

    # Logout
    client.get("/logout")

    # User 2
    client.post("/signup", data={
        "email": "user2@example.com",
        "password": "Password123"
    })

    # Attempt to access user1's evaluation
    response = client.get(f"/api/evaluations/{eval_id}")

    assert response.status_code == 404


# ------------------------------------------------------------
# Pagination test
# ------------------------------------------------------------

def test_pagination_works(client):

    client.post("/signup", data={
        "email": "pagination@example.com",
        "password": "Password123"
    })

    client.post("/profile", data={
        "renter_type": "worker",
        "monthly_income": 30000,
        "renter_docs": ["bank statement", "payslip"]
    })

    for i in range(15):
        client.post("/evaluate", data={
            "listing_name": f"Listing {i}",
            "rent": 8000,
            "deposit": 8000,
            "application_fee": 0,
            "area_demand": "MEDIUM",
            "required_documents": []
        })

    response = client.get("/api/evaluations?limit=5&offset=0")
    data = response.json()

    assert data["total"] == 15
    assert len(data["evaluations"]) == 5

