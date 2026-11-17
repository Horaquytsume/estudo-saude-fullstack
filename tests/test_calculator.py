import importlib.util
import math
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("calculator", Path(__file__).resolve().parents[1] / "python-engine" / "calculator.py")
calculator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(calculator)


class InfusionCalculationTests(unittest.TestCase):
    def test_known_educational_example(self):
        result = calculator.calculate_infusion({"dose": 5, "weight": 70, "drug_mg": 200, "volume_ml": 250})
        self.assertEqual(result["infusion_rate_ml_h"], 26.25)
        self.assertEqual(result["concentration_mcg_ml"], 800)

    def test_rejects_nonpositive_boolean_and_nonfinite(self):
        baseline = {"dose": 5, "weight": 70, "drug_mg": 200, "volume_ml": 250}
        for value in (0, -1, True, math.inf, math.nan):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    calculator.calculate_infusion({**baseline, "dose": value})

    def test_rejects_intermediate_overflow_and_underflow(self):
        for case in (
            {"dose": 1, "weight": 1, "drug_mg": 1e308, "volume_ml": 1},
            {"dose": 1, "weight": 1, "drug_mg": 1e-300, "volume_ml": 1e300},
            {"dose": 1e308, "weight": 1e308, "drug_mg": 1, "volume_ml": 1},
        ):
            with self.subTest(case=case):
                with self.assertRaises(ValueError):
                    calculator.calculate_infusion(case)


if __name__ == "__main__":
    unittest.main()
