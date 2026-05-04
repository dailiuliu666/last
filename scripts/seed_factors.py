from app.core.database import SessionLocal
from app.services.quant.factor_service import FactorService


if __name__ == "__main__":
    db = SessionLocal()
    try:
        created = FactorService().create_builtin_factors(db)
        print(f"Builtin factors created: {created}")
    finally:
        db.close()
