"""Calculadora didática de vazão; não substitui prescrição nem validação clínica."""
import json
import math
import sys


def positive_number(data, key):
    value = data.get(key)
    if isinstance(value, bool):
        raise ValueError(f"'{key}' precisa ser um número maior que zero.")
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"'{key}' precisa ser um número maior que zero.")
    if not math.isfinite(number) or number <= 0:
        raise ValueError(f"'{key}' precisa ser um número finito maior que zero.")
    return number


def calculate_infusion(data):
    if not isinstance(data, dict):
        raise ValueError("O corpo da requisição precisa ser um objeto JSON.")
    dose = positive_number(data, "dose")  # mcg/kg/min
    weight = positive_number(data, "weight")  # kg
    drug_mg = positive_number(data, "drug_mg")  # mg no volume total
    volume_ml = positive_number(data, "volume_ml")  # mL

    concentration_mcg_ml = (drug_mg * 1000) / volume_ml
    infusion_rate_ml_h = (dose * weight * 60) / concentration_mcg_ml
    return {
        "status": "success",
        "infusion_rate_ml_h": round(infusion_rate_ml_h, 2),
        "concentration_mcg_ml": round(concentration_mcg_ml, 2),
        "units": {"dose": "mcg/kg/min", "weight": "kg", "drug": "mg", "volume": "mL"},
    }


if __name__ == "__main__":
    try:
        raw = sys.stdin.read()
        result = calculate_infusion(json.loads(raw))
    except (json.JSONDecodeError, ValueError) as exc:
        result = {"status": "error", "message": str(exc)}
    except Exception:
        result = {"status": "error", "message": "Não foi possível realizar o cálculo."}
    print(json.dumps(result, ensure_ascii=False))
