from app import create_app, db
from app.models import User

app = create_app()

with app.app_context():
    # Count all users
    total_users = User.query.count()
    print(f"Total number of users: {total_users}")

    # Count admins (assuming 'admin' is the username for admins)
    admin_count = User.query.filter_by(username='admin').count()
    print(f"Total number of admins: {admin_count}")
