from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.quant import (
    CustomFactorCreate,
    QuantModelCreate,
    QuantModelPredictRequest,
    QuantModelTrainRequest,
    QuantScoreRequest,
)
from app.services.quant.factor_calc_service import FactorCalculationService
from app.services.quant.data_sync_service import QuantDataSyncService
from app.services.quant.factor_service import FactorService
from app.services.quant.model_service import QuantModelService
from app.services.quant.scoring_service import QuantScoringService


router = APIRouter(prefix="/api/quant", tags=["quant"])
sync_service = QuantDataSyncService()
factor_service = FactorService()
factor_calc_service = FactorCalculationService()
model_service = QuantModelService()
scoring_service = QuantScoringService()


def dump_model(payload):
    return payload.model_dump() if hasattr(payload, "model_dump") else payload.dict()


@router.get("/health")
def health():
    return {"success": True, "services": {"database": "configured", "tushare": sync_service.health()}}


@router.get("/overview")
def overview(db: Session = Depends(get_db)):
    try:
        return scoring_service.get_quant_overview(db)
    except Exception as exc:
        return {"success": False, "message": str(exc)}


@router.post("/sync/star-board/basic")
def sync_star_board_basic(db: Session = Depends(get_db)):
    try:
        return sync_service.sync_star_board_basic(db)
    except Exception as exc:
        return {"success": False, "message": str(exc)}


@router.post("/sync/star-board/daily")
def sync_star_board_daily(
    start_date: str = Query(..., description="Format: YYYYMMDD"),
    end_date: str | None = Query(None, description="Format: YYYYMMDD"),
    limit: int | None = Query(None, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    try:
        return sync_service.sync_star_board_daily(db, start_date=start_date, end_date=end_date, limit=limit)
    except Exception as exc:
        return {"success": False, "message": str(exc)}


@router.post("/factors/bootstrap")
def bootstrap_factors(db: Session = Depends(get_db)):
    created = factor_service.create_builtin_factors(db)
    return {"success": True, "created": created}


@router.post("/factors/calculate")
def calculate_factors(
    trade_date: str = Query(..., description="Format: YYYYMMDD"),
    limit: int | None = Query(None, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    try:
        return factor_calc_service.calculate_for_trade_date(db, trade_date=trade_date, limit=limit)
    except Exception as exc:
        return {"success": False, "message": str(exc)}


@router.post("/factors/calculate-range")
def calculate_factors_range(
    start_date: str = Query(..., description="Format: YYYYMMDD"),
    end_date: str = Query(..., description="Format: YYYYMMDD"),
    limit: int | None = Query(None, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    try:
        return factor_calc_service.calculate_for_date_range(
            db,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
        )
    except Exception as exc:
        return {"success": False, "message": str(exc)}


@router.get("/factors")
def list_factors(db: Session = Depends(get_db)):
    factors = factor_service.list_factors(db)
    return {
        "success": True,
        "factors": [
            {
                "factor_id": item.factor_id,
                "factor_name": item.factor_name,
                "factor_type": item.factor_type,
                "formula": item.formula,
                "description": item.description,
                "params": item.params or {},
                "direction": (item.params or {}).get("direction", 1),
                "weight": (item.params or {}).get("weight", 1.0),
                "is_builtin": item.is_builtin,
                "is_active": item.is_active,
            }
            for item in factors
        ],
    }


@router.post("/factors/custom")
def create_custom_factor(payload: CustomFactorCreate, db: Session = Depends(get_db)):
    try:
        return factor_service.create_custom_factor(
            db,
            factor_id=payload.factor_id,
            factor_name=payload.factor_name,
            factor_type=payload.factor_type,
            formula=payload.formula,
            description=payload.description,
            direction=payload.direction,
            weight=payload.weight,
        )
    except Exception as exc:
        return {"success": False, "message": str(exc), "factor": dump_model(payload)}


@router.get("/models/capabilities")
def model_capabilities():
    return {"success": True, "capabilities": model_service.capabilities()}


@router.get("/models")
def list_models(db: Session = Depends(get_db)):
    return {"success": True, "models": model_service.list_model_definitions(db)}


@router.post("/models")
def create_model(payload: QuantModelCreate, db: Session = Depends(get_db)):
    try:
        return model_service.create_model_definition(
            db,
            model_id=payload.model_id,
            model_name=payload.model_name,
            model_type=payload.model_type,
            target_type=payload.target_type,
            factor_list=payload.factor_list,
        )
    except Exception as exc:
        return {"success": False, "message": str(exc)}


@router.post("/models/train")
def train_model(payload: QuantModelTrainRequest, db: Session = Depends(get_db)):
    try:
        return model_service.train_model(
            db,
            model_id=payload.model_id,
            start_date=payload.start_date,
            end_date=payload.end_date,
        )
    except Exception as exc:
        return {"success": False, "message": str(exc)}


@router.post("/models/predict")
def predict_model(payload: QuantModelPredictRequest, db: Session = Depends(get_db)):
    try:
        return model_service.predict_scores(
            db,
            model_id=payload.model_id,
            trade_date=payload.trade_date,
        )
    except Exception as exc:
        return {"success": False, "message": str(exc)}


@router.post("/scores")
def calculate_scores(payload: QuantScoreRequest, db: Session = Depends(get_db)):
    try:
        return scoring_service.calculate_scores(db, trade_date=payload.trade_date, factor_ids=payload.factor_ids)
    except Exception as exc:
        return {"success": False, "message": str(exc)}


@router.get("/stocks/{ts_code}/factors")
def stock_factor_snapshot(ts_code: str, trade_date: str, db: Session = Depends(get_db)):
    try:
        return scoring_service.get_stock_factor_snapshot(db, ts_code=ts_code, trade_date=trade_date)
    except Exception as exc:
        return {"success": False, "message": str(exc)}


@router.get("/models/{model_id}/stocks/{ts_code}/prediction")
def stock_prediction_snapshot(model_id: str, ts_code: str, trade_date: str, db: Session = Depends(get_db)):
    try:
        return model_service.get_stock_prediction_snapshot(db, model_id=model_id, ts_code=ts_code, trade_date=trade_date)
    except Exception as exc:
        return {"success": False, "message": str(exc)}
