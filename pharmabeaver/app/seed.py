# app/seed.py
from app.app import app, db, User, Product

def create_and_seed(drop=False):
    if drop:
        # only for local dev resets; comment out in shared environments
        db.drop_all()
    db.create_all()

    # --- Users (3) ---
    if User.query.count() == 0:
        users = []
        for uname in ["alice", "bob", "charlie"]:
            u = User(username=uname)
            u.set_password("password123")
            users.append(u)
        db.session.add_all(users)
        db.session.commit()

    # --- Products (6, incl. Insulin Rx) ---
    if Product.query.count() == 0:
        products = [
            Product(
                name="Acme Vitamin C 500mg (100ct)",
                price_cents=899,
                description="Daily vitamin C tablets. 100 count bottle.",
                image_url="https://placehold.co/600x400?text=Vitamin+C",
                prescription_required=False,
            ),
            Product(
                name="Herbal Sleep Tea (20 bags)",
                price_cents=599,
                description="Caffeine-free blend to unwind before bed.",
                image_url="https://placehold.co/600x400?text=Sleep+Tea",
                prescription_required=False,
            ),
            Product(
                name="Allergy Relief Tabs (24ct)",
                price_cents=1299,
                description="Antihistamine tablets for seasonal allergies.",
                image_url="https://placehold.co/600x400?text=Allergy+Relief",
                prescription_required=False,
            ),
            Product(
                name="Pain Relief Gel 3oz",
                price_cents=1099,
                description="Topical gel for minor aches and pains.",
                image_url="https://placehold.co/600x400?text=Pain+Gel",
                prescription_required=False,
            ),
            Product(
                name="Insulin 100 units/mL (10mL vial)",
                price_cents=3499,
                description="Prescription insulin vial. Use only under medical supervision.",
                image_url="https://placehold.co/600x400?text=Insulin+Rx",
                prescription_required=True,
            ),
            Product(
                name="Omega-3 Fish Oil (120 softgels)",
                price_cents=1899,
                description="EPA/DHA supplement from fish oil.",
                image_url="https://placehold.co/600x400?text=Omega-3",
                prescription_required=False,
            ),
        ]
        db.session.add_all(products)
        db.session.commit()

    print("Seed complete.")

if __name__ == "__main__":
    with app.app_context():
        # set drop=True if you want a clean slate locally
        create_and_seed(drop=False)
