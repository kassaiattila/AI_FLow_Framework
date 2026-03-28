"""
@test_registry:
    suite: models-unit
    component: models.cost
    covers: [src/aiflow/models/cost.py]
    phase: 2
    priority: high
    estimated_duration_ms: 100
    requires_services: []
    tags: [models, cost, pricing, budget]
"""
from aiflow.models.cost import ModelCostCalculator

class TestModelCostCalculator:
    def test_known_model_cost(self):
        calc = ModelCostCalculator()
        cost = calc.calculate("openai/gpt-4o", input_tokens=1000, output_tokens=500)
        assert cost > 0

    def test_unknown_model_returns_zero(self):
        calc = ModelCostCalculator()
        cost = calc.calculate("unknown/model", input_tokens=1000, output_tokens=500)
        assert cost == 0.0

    def test_gpt4o_mini_cheaper(self):
        calc = ModelCostCalculator()
        cost_4o = calc.calculate("openai/gpt-4o", 1000, 500)
        cost_mini = calc.calculate("openai/gpt-4o-mini", 1000, 500)
        assert cost_mini < cost_4o

    def test_embedding_no_output_cost(self):
        calc = ModelCostCalculator()
        cost = calc.calculate("openai/text-embedding-3-small", input_tokens=1000, output_tokens=0)
        assert cost > 0

    def test_custom_pricing(self):
        calc = ModelCostCalculator(custom_pricing={"my/model": {"input": 1.0, "output": 2.0}})
        cost = calc.calculate("my/model", input_tokens=1_000_000, output_tokens=500_000)
        assert cost == 2.0  # 1.0 + 1.0

    def test_register_pricing(self):
        calc = ModelCostCalculator()
        calc.register_pricing("new/model", input_per_million=5.0, output_per_million=10.0)
        assert calc.get_pricing("new/model") is not None
        cost = calc.calculate("new/model", 1_000_000, 1_000_000)
        assert cost == 15.0

    def test_list_priced_models(self):
        calc = ModelCostCalculator()
        models = calc.list_priced_models()
        assert "openai/gpt-4o" in models
        assert len(models) >= 5

    def test_estimate_cost(self):
        calc = ModelCostCalculator()
        cost = calc.estimate_cost("openai/gpt-4o-mini", 500, 200)
        assert cost >= 0
