"""
Risk Scoring Evaluator Module
Categorizes continuous cheating probability scores into LOW, MEDIUM, or HIGH risk.
"""

from config import FUSION_CONFIG


class RiskScorer:
    """
    Modular Risk Classification interface.
    """

    def __init__(self):
        self.low_threshold = FUSION_CONFIG["RISK_THRESHOLD_LOW"]
        self.medium_threshold = FUSION_CONFIG["RISK_THRESHOLD_MEDIUM"]

    def evaluate_risk_level(self, score):
        """
        Classifies numerical score into risk level string.
        """
        if score < self.low_threshold:
            return "LOW"
        elif score < self.medium_threshold:
            return "MEDIUM"
        return "HIGH"
