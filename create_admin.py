from app import create_app, db
from app.models import User

app = create_app()

with app.app_context():
    username = "oneway"
    password = "Omarelshall_"

    admin = User.query.filter_by(username=username).first()
    if not admin:
        admin = User(username=username)
        admin.set_password(password)
        db.session.add(admin)
        db.session.commit()
        print("Admin user created successfully.")
    else:
        print("Admin user already exists.")
