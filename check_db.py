#!/usr/bin/env python
# -*- coding: utf-8 -*-

# 检查数据库内容的脚本

import sys
from pathlib import Path

# 添加项目根目录到路径
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from app.core.database import SessionLocal
from app.models.stock_basic import StockBasic
from app.models.stock_daily import StockDaily
from app.models.factor_definition import FactorDefinition
from app.models.factor_value import FactorValue
from app.models.ml_model_definition import MLModelDefinition
from app.models.ml_prediction import MLPrediction
from app.models.train_run import TrainRun
from app.core.config import settings


def main():
    print("=" * 60)
    print(f"数据库连接：{settings.database_url}")
    print("=" * 60)

    db = SessionLocal()
    try:
        # 检查表数据
        tables = [
            ("stock_basic", StockBasic, "ts_code"),
            ("stock_daily", StockDaily, "id"),
            ("factor_definition", FactorDefinition, "factor_id"),
            ("factor_value", FactorValue, "id"),
            ("ml_model_definition", MLModelDefinition, "model_id"),
            ("ml_prediction", MLPrediction, "id"),
            ("train_run", TrainRun, "id"),
        ]

        for table_name, model, pk_field in tables:
            count = db.query(model).count()
            print(f"\n📊 {table_name}: {count} 条记录")

            if count > 0:
                items = db.query(model).limit(5).all()
                print("  前5条记录预览:")
                for item in items:
                    pk_val = getattr(item, pk_field)
                    print(f"  - {pk_val}")

        print("\n" + "=" * 60)
        print("检查完成！")
        print("=" * 60)

    finally:
        db.close()


if __name__ == "__main__":
    main()
