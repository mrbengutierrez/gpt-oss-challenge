# app/seed.py
from datetime import datetime, timedelta
from app.app import app, db, User, Product, Order, OrderItem


def create_and_seed(drop: bool = False):
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
                image_url="/static/vitamin_c.png",
                prescription_required=False,
            ),
            Product(
                name="Emergency Contraception 1.5mg (1 tab)",
                price_cents=3999,
                description="Over-the-counter levonorgestrel tablet. Follow package directions.",
                image_url="/static/emergency_contraception.png",
                prescription_required=False,
            ),
            Product(
                name="At-Home Pregnancy Test (2ct)",
                price_cents=1299,
                description="Rapid urine pregnancy tests. Read instructions before use.",
                image_url="/static/pregnancy_test.png",
                prescription_required=False,
            ),
            Product(
                name="Yeast Infection Treatment 3-Day (Clotrimazole)",
                price_cents=1099,
                description="OTC 3-day vaginal antifungal treatment. Use as directed.",
                image_url="/static/clotrimazole.png",
                prescription_required=False,
            ),
            Product(
                name="Insulin 100 units/mL (10mL vial)",
                price_cents=3499,
                description="Prescription insulin vial. Use only under medical supervision.",
                image_url="/static/insulin.png",
                prescription_required=True,
            ),
            Product(
                name="Omega-3 Fish Oil (120 softgels)",
                price_cents=1899,
                description="EPA/DHA supplement from fish oil.",
                image_url="/static/fish_oil.png",
                prescription_required=False,
            ),
        ]
        db.session.add_all(products)
        db.session.commit()


    # --- Orders & OrderItems (create only if none exist) ---
    if Order.query.count() == 0:
        users = {u.username: u for u in User.query.all()}
        prods = {p.name: p for p in Product.query.all()}
        now = datetime.utcnow()

        def make_order(user, days_ago: int, items: list[tuple[str, int]]):
            order = Order(user_id=user.id, created_at=now - timedelta(days=days_ago))
            db.session.add(order)
            db.session.flush()  # to get order.id

            for prod_name, qty in items:
                p = prods[prod_name]
                db.session.add(
                    OrderItem(
                        order_id=order.id,
                        product_id=p.id,
                        quantity=qty,
                        price_cents_snapshot=p.price_cents,
                    )
                )
            db.session.commit()

        # alice: vitamins + omega, later a pregnancy test
        make_order(
            users["alice"],
            days_ago=14,
            items=[
                ("Acme Vitamin C 500mg (100ct)", 2),
                ("Omega-3 Fish Oil (120 softgels)", 1),
            ],
        )
        make_order(
            users["alice"],
            days_ago=3,
            items=[
                ("At-Home Pregnancy Test (2ct)", 1),
                ("Insulin 100 units/mL (10mL vial)", 1),
            ],
        )

        # bob: emergency contraception earlier, later antifungal + vitamin C
        make_order(
            users["bob"],
            days_ago=21,
            items=[
                ("Emergency Contraception 1.5mg (1 tab)", 1),
            ],
        )
        make_order(
            users["bob"],
            days_ago=5,
            items=[
                ("Yeast Infection Treatment 3-Day (Clotrimazole)", 1),
                ("Acme Vitamin C 500mg (100ct)", 1),
            ],
        )

        # charlie: omega-3 bulk earlier, recent insulin (Rx flagged product)
        make_order(
            users["charlie"],
            days_ago=30,
            items=[
                ("Omega-3 Fish Oil (120 softgels)", 2),
            ],
        )
        make_order(
            users["charlie"],
            days_ago=1,
            items=[
                ("Insulin 100 units/mL (10mL vial)", 1),
            ],
        )

        print("Seeded orders and order items.")

    print("Seed complete.")


if __name__ == "__main__":
    with app.app_context():
        # set drop=True if you want a clean slate locally
        create_and_seed(drop=False)
