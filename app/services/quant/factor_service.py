import ast
import re
from typing import List, Tuple

from sqlalchemy.orm import Session

from app.models.factor_definition import FactorDefinition


BUILTIN_FACTORS = [
    {
        "factor_id": "return_1d",
        "factor_name": "1日收益率",
        "factor_type": "momentum",
        "formula": "close.pct_change(1)",
        "description": "最近1个交易日收盘价收益率，数值越高代表短期表现越强。",
        "params": {"direction": 1, "weight": 0.8},
    },
    {
        "factor_id": "return_3d",
        "factor_name": "3日收益率",
        "factor_type": "momentum",
        "formula": "close.pct_change(3)",
        "description": "最近3个交易日收盘价收益率，用于观察超短期价格表现。",
        "params": {"direction": 1, "weight": 0.8},
    },
    {
        "factor_id": "momentum_5d",
        "factor_name": "5日动量",
        "factor_type": "momentum",
        "formula": "close.pct_change(5)",
        "description": "最近5个交易日收盘价收益率，数值越高代表短期趋势越强。",
        "params": {"direction": 1, "weight": 1.0},
    },
    {
        "factor_id": "momentum_10d",
        "factor_name": "10日动量",
        "factor_type": "momentum",
        "formula": "close.pct_change(10)",
        "description": "最近10个交易日收盘价收益率，用于衡量短中期趋势。",
        "params": {"direction": 1, "weight": 1.0},
    },
    {
        "factor_id": "momentum_20d",
        "factor_name": "20日动量",
        "factor_type": "momentum",
        "formula": "close.pct_change(20)",
        "description": "最近20个交易日收盘价收益率，数值越高代表中期趋势越强。",
        "params": {"direction": 1, "weight": 1.0},
    },
    {
        "factor_id": "momentum_60d",
        "factor_name": "60日动量",
        "factor_type": "momentum",
        "formula": "close.pct_change(60)",
        "description": "最近60个交易日收盘价收益率，用于衡量中期趋势。",
        "params": {"direction": 1, "weight": 0.8},
    },
    {
        "factor_id": "ma5_deviation",
        "factor_name": "5日均线偏离率",
        "factor_type": "trend",
        "formula": "close / close.rolling(5).mean() - 1",
        "description": "收盘价相对5日均线的偏离程度。",
        "params": {"direction": 1, "weight": 0.7},
    },
    {
        "factor_id": "ma20_deviation",
        "factor_name": "20日均线偏离率",
        "factor_type": "trend",
        "formula": "close / close.rolling(20).mean() - 1",
        "description": "收盘价相对20日均线的偏离程度。",
        "params": {"direction": 1, "weight": 0.8},
    },
    {
        "factor_id": "ma5_ma20_gap",
        "factor_name": "5日/20日均线差",
        "factor_type": "trend",
        "formula": "close.rolling(5).mean() / close.rolling(20).mean() - 1",
        "description": "5日均线相对20日均线的强弱，反映短期趋势是否强于中期趋势。",
        "params": {"direction": 1, "weight": 0.8},
    },
    {
        "factor_id": "volatility_5d",
        "factor_name": "5日波动率",
        "factor_type": "volatility",
        "formula": "close.pct_change().rolling(5).std()",
        "description": "最近5个交易日收益率标准差，默认按低波动更优处理。",
        "params": {"direction": -1, "weight": 0.6},
    },
    {
        "factor_id": "volatility_20d",
        "factor_name": "20日波动率",
        "factor_type": "volatility",
        "formula": "close.pct_change().rolling(20).std()",
        "description": "最近20个交易日收益率标准差，默认按低波动更优处理。",
        "params": {"direction": -1, "weight": 0.8},
    },
    {
        "factor_id": "volatility_60d",
        "factor_name": "60日波动率",
        "factor_type": "volatility",
        "formula": "close.pct_change().rolling(60).std()",
        "description": "最近60个交易日收益率标准差，默认按低波动更优处理。",
        "params": {"direction": -1, "weight": 0.6},
    },
    {
        "factor_id": "amplitude_20d",
        "factor_name": "20日平均振幅",
        "factor_type": "volatility",
        "formula": "((high - low) / close).rolling(20).mean()",
        "description": "最近20个交易日平均日内振幅，默认按振幅越低越稳定处理。",
        "params": {"direction": -1, "weight": 0.6},
    },
    {
        "factor_id": "turnover_amount_5d",
        "factor_name": "5日平均成交额",
        "factor_type": "liquidity",
        "formula": "amount.rolling(5).mean()",
        "description": "最近5个交易日平均成交额，用于衡量短期市场关注度和流动性。",
        "params": {"direction": 1, "weight": 0.6},
    },
    {
        "factor_id": "turnover_amount_20d",
        "factor_name": "20日平均成交额",
        "factor_type": "liquidity",
        "formula": "amount.rolling(20).mean()",
        "description": "最近20个交易日平均成交额，用于衡量流动性和市场关注度。",
        "params": {"direction": 1, "weight": 0.7},
    },
    {
        "factor_id": "turnover_amount_60d",
        "factor_name": "60日平均成交额",
        "factor_type": "liquidity",
        "formula": "amount.rolling(60).mean()",
        "description": "最近60个交易日平均成交额，用于衡量中期流动性。",
        "params": {"direction": 1, "weight": 0.5},
    },
    {
        "factor_id": "amount_ratio_5d_20d",
        "factor_name": "5日/20日成交额比",
        "factor_type": "liquidity",
        "formula": "amount.rolling(5).mean() / amount.rolling(20).mean()",
        "description": "短期成交额相对中期成交额的放大程度。",
        "params": {"direction": 1, "weight": 0.7},
    },
    {
        "factor_id": "volume_ratio_5d_20d",
        "factor_name": "5日/20日成交量比",
        "factor_type": "liquidity",
        "formula": "vol.rolling(5).mean() / vol.rolling(20).mean()",
        "description": "短期成交量相对中期成交量的放大程度。",
        "params": {"direction": 1, "weight": 0.7},
    },
    {
        "factor_id": "volume_ratio_10d_60d",
        "factor_name": "10日/60日成交量比",
        "factor_type": "liquidity",
        "formula": "vol.rolling(10).mean() / vol.rolling(60).mean()",
        "description": "短期成交量相对中期成交量的变化，用于观察量能是否放大。",
        "params": {"direction": 1, "weight": 0.6},
    },
    {
        "factor_id": "price_position_20d",
        "factor_name": "20日价格位置",
        "factor_type": "technical",
        "formula": "(close - low.rolling(20).min()) / (high.rolling(20).max() - low.rolling(20).min())",
        "description": "收盘价在近20日高低区间中的位置，越接近1表示越接近阶段高位。",
        "params": {"direction": 1, "weight": 0.6},
    },
    {
        "factor_id": "price_position_60d",
        "factor_name": "60日价格位置",
        "factor_type": "technical",
        "formula": "(close - low.rolling(60).min()) / (high.rolling(60).max() - low.rolling(60).min())",
        "description": "收盘价在近60日高低区间中的位置，越接近1表示越接近阶段高位。",
        "params": {"direction": 1, "weight": 0.5},
    },
    {
        "factor_id": "intraday_strength",
        "factor_name": "日内收盘强度",
        "factor_type": "technical",
        "formula": "(close - low) / (high - low)",
        "description": "收盘价在当日高低区间中的位置，越高表示收盘越强。",
        "params": {"direction": 1, "weight": 0.5},
    },
]


class FactorService:
    allowed_names = {
        "open",
        "high",
        "low",
        "close",
        "vol",
        "amount",
    }
    allowed_methods = {
        "pct_change",
        "rolling",
        "mean",
        "std",
        "shift",
        "abs",
        "min",
        "max",
        "sum",
    }
    blocked_pattern = re.compile(r"(__|import|eval|exec|open|read|write|compile|globals|locals|lambda)", re.I)

    def list_factors(self, db: Session) -> List[FactorDefinition]:
        return db.query(FactorDefinition).order_by(FactorDefinition.factor_id.asc()).all()

    def create_builtin_factors(self, db: Session) -> int:
        changed = 0
        for item in BUILTIN_FACTORS:
            exists = db.query(FactorDefinition).filter_by(factor_id=item["factor_id"]).first()
            if exists:
                exists.factor_name = item["factor_name"]
                exists.factor_type = item["factor_type"]
                exists.formula = item["formula"]
                exists.description = item["description"]
                exists.params = item.get("params", {})
                exists.is_builtin = True
                exists.is_active = True
            else:
                db.add(FactorDefinition(**item, is_builtin=True, is_active=True))
            changed += 1
        db.commit()
        return changed

    def create_custom_factor(
        self,
        db: Session,
        factor_id: str,
        factor_name: str,
        factor_type: str,
        formula: str,
        description: str | None = None,
        direction: int = 1,
        weight: float = 1.0,
    ) -> dict:
        if direction not in (1, -1):
            return {"success": False, "message": "direction must be 1 or -1"}
        if weight < 0:
            return {"success": False, "message": "weight must be greater than or equal to 0"}

        valid, message = self.validate_formula(formula)
        if not valid:
            return {"success": False, "message": message}

        payload = {
            "factor_name": factor_name,
            "factor_type": factor_type,
            "formula": formula,
            "description": description,
            "params": {"direction": direction, "weight": weight},
            "is_builtin": False,
            "is_active": True,
        }
        existing = db.get(FactorDefinition, factor_id)
        if existing:
            for key, value in payload.items():
                setattr(existing, key, value)
            action = "updated"
        else:
            db.add(FactorDefinition(factor_id=factor_id, **payload))
            action = "created"
        db.commit()
        return {"success": True, "message": f"Custom factor {action}", "factor_id": factor_id}

    def validate_formula(self, formula: str) -> Tuple[bool, str]:
        if not formula or not formula.strip():
            return False, "Formula cannot be empty"
        if self.blocked_pattern.search(formula):
            return False, "Formula contains unsafe keyword"

        try:
            tree = ast.parse(formula, mode="eval")
        except SyntaxError as exc:
            return False, f"Formula syntax error: {exc.msg}"

        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id not in self.allowed_names:
                return False, f"Formula contains unsupported name: {node.id}"
            if isinstance(node, ast.Attribute) and node.attr not in self.allowed_methods:
                return False, f"Formula contains unsupported method: {node.attr}"
            if isinstance(node, ast.Call):
                if not isinstance(node.func, ast.Attribute):
                    return False, "Only pandas Series method calls are supported"
            if not isinstance(
                node,
                (
                    ast.Expression,
                    ast.BinOp,
                    ast.UnaryOp,
                    ast.Call,
                    ast.Attribute,
                    ast.Name,
                    ast.Load,
                    ast.Constant,
                    ast.Add,
                    ast.Sub,
                    ast.Mult,
                    ast.Div,
                    ast.Pow,
                    ast.USub,
                    ast.UAdd,
                ),
            ):
                return False, f"Formula contains unsupported syntax: {node.__class__.__name__}"
        return True, ""
