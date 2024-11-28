from app import create_app, db
from app.models import User

app = create_app()

with app.app_context():
    db.create_all()

    if not User.query.filter_by(username="admin").first():
        admin = User(username="admin")
        admin.set_password("securepassword123")
        db.session.add(admin)
        db.session.commit()
        print("Admin user created successfully.")
    else:
        print("Admin user already exists.")
