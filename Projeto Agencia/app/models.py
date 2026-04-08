"""
Modelos de dados para o dashboard da agência.
"""
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()


class User(db.Model):
    """Usuário do sistema."""
    __tablename__ = 'users'

    username = db.Column(db.String(80), primary_key=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='viewer')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_first_login = db.Column(db.Boolean, default=True)

    ROLES = ['admin', 'orcamento', 'viewer']

    def set_password(self, password):
        """Hash e salva a senha."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verifica se a senha está correta."""
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        """Retorna dados públicos do usuário."""
        return {
            'username': self.username,
            'role': self.role,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_first_login': self.is_first_login
        }
