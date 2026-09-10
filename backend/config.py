import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", "sqlite:///academia.db"
    )
    # Render usa postgresql:// mas SQLAlchemy precisa de postgresql+psycopg2://
    if SQLALCHEMY_DATABASE_URI and SQLALCHEMY_DATABASE_URI.startswith("postgresql://"):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace(
            "postgresql://", "postgresql+psycopg2://", 1
        )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Session security
    SESSION_COOKIE_SECURE = False  # True apenas em produção com HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hora


class DevelopmentConfig(Config):
    DEBUG = True
    # Em desenvolvimento, permite SECRET_KEY padrão se não definida
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True  # Requer HTTPS em produção


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
