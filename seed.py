from app.database import SessionLocal
from app.models import User
from app.security import get_password_hash


def seed():
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == 'patient@healthdelt.com').first()
        if existing:
            print('Demo user already exists:', existing.email)
        else:
            print('No demo patient found, creating...')
            user = User(
                fullName='Demo Patient',
                email='patient@healthdelt.com',
                passwordHash=get_password_hash('Password@123'),
                passwordRaw=None,
                role='PATIENT',
                status='ACTIVE',
            )
            db.add(user)
            db.commit()
            print('Created demo user: patient@healthdelt.com / Password@123')
        # Create admin user
        admin = db.query(User).filter(User.email == 'admin@helthdelt.com').first()
        if admin:
            print('Admin user already exists:', admin.email)
        else:
            admin_user = User(
                fullName='Healthdelt Admin',
                email='admin@helthdelt.com',
                passwordHash=get_password_hash('Password@123'),
                passwordRaw=None,
                role='ADMIN',
                status='ACTIVE',
            )
            db.add(admin_user)
            db.commit()
            print('Created admin user: admin@helthdelt.com / Password@123')
    finally:
        db.close()


if __name__ == '__main__':
    seed()
