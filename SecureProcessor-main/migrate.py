from app import app, db, User
with app.app_context():
    old_admin = User.query.filter_by(username='admin').first()
    if old_admin:
        db.session.delete(old_admin)
        db.session.commit()
        print('Deleted old admin')
