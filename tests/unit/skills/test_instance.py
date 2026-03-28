"""
@test_registry:
    suite: skills-unit
    component: skills.instance
    covers: [src/aiflow/skills/instance.py]
    phase: A
    priority: critical
    estimated_duration_ms: 200
    requires_services: []
    tags: [skills, instance, pydantic, config]
"""
import pytest

from aiflow.skills.instance import (
    InstanceConfig,
    DataSourceConfig,
    CollectionRef,
    PromptConfig,
    PromptOverride,
    ModelConfig,
    BudgetConfig,
    SLAConfig,
    IntentConfig,
    RoutingConfig,
)


class TestCollectionRef:
    def test_defaults(self) -> None:
        ref = CollectionRef(name="my-collection")
        assert ref.name == "my-collection"
        assert ref.priority == 1

    def test_custom_priority(self) -> None:
        ref = CollectionRef(name="old-docs", priority=3)
        assert ref.priority == 3


class TestDataSourceConfig:
    def test_defaults(self) -> None:
        ds = DataSourceConfig()
        assert ds.collections == []
        assert ds.document_filters == {}
        assert ds.embedding_model == "text-embedding-3-small"

    def test_with_collections(self) -> None:
        ds = DataSourceConfig(
            collections=[CollectionRef(name="c1"), CollectionRef(name="c2", priority=2)],
            document_filters={"language": "hu"},
        )
        assert len(ds.collections) == 2
        assert ds.document_filters["language"] == "hu"


class TestPromptConfig:
    def test_minimal(self) -> None:
        pc = PromptConfig(namespace="test/ns")
        assert pc.namespace == "test/ns"
        assert pc.label == "prod"
        assert pc.overrides == []

    def test_with_overrides(self) -> None:
        pc = PromptConfig(
            namespace="azhu/rag",
            label="staging",
            overrides=[
                PromptOverride(
                    prompt_name="system-prompt",
                    variables={"company_name": "Test Corp"},
                )
            ],
        )
        assert len(pc.overrides) == 1
        assert pc.overrides[0].prompt_name == "system-prompt"
        assert pc.overrides[0].variables["company_name"] == "Test Corp"
        assert pc.overrides[0].template is None


class TestModelConfig:
    def test_defaults(self) -> None:
        mc = ModelConfig()
        assert mc.default == "gpt-4o"
        assert mc.fallback == "gpt-4o-mini"
        assert mc.per_agent == {}

    def test_per_agent_override(self) -> None:
        mc = ModelConfig(
            default="gpt-4o",
            per_agent={"classifier": "gpt-4o-mini"},
        )
        assert mc.per_agent["classifier"] == "gpt-4o-mini"


class TestBudgetConfig:
    def test_defaults(self) -> None:
        bc = BudgetConfig()
        assert bc.monthly_usd == 100.0
        assert bc.per_run_usd == 0.50
        assert bc.alert_threshold == 0.8


class TestSLAConfig:
    def test_defaults(self) -> None:
        sc = SLAConfig()
        assert sc.target_seconds == 10
        assert sc.p95_target_seconds == 20
        assert sc.availability == 0.99


class TestIntentConfig:
    def test_full(self) -> None:
        ic = IntentConfig(
            name="claim_report",
            description="New claim",
            handler="extract_claim",
            priority=1,
            auto_respond=False,
        )
        assert ic.name == "claim_report"
        assert ic.auto_respond is False


class TestRoutingConfig:
    def test_defaults(self) -> None:
        rc = RoutingConfig()
        assert rc.input_channel == "api"
        assert rc.output_channel == "api"
        assert rc.webhook_url is None
        assert rc.queue_name is None


class TestInstanceConfig:
    def test_minimal(self) -> None:
        config = InstanceConfig(
            instance_name="test-instance",
            skill_template="aszf_rag_chat",
            customer="testco",
            prompts=PromptConfig(namespace="testco/rag"),
        )
        assert config.instance_name == "test-instance"
        assert config.skill_template == "aszf_rag_chat"
        assert config.customer == "testco"
        assert config.enabled is True
        assert config.version == "0.1.0"
        assert config.models.default == "gpt-4o"

    def test_full_config(self) -> None:
        config = InstanceConfig(
            instance_name="azhu-aszf-rag",
            display_name="AZHU ASZF Chatbot",
            skill_template="aszf_rag_chat",
            version="1.2.0",
            customer="azhu",
            enabled=True,
            data_sources=DataSourceConfig(
                collections=[CollectionRef(name="azhu-aszf-2024")],
                document_filters={"document_type": "aszf"},
            ),
            prompts=PromptConfig(
                namespace="azhu/aszf-rag",
                label="prod",
                overrides=[
                    PromptOverride(
                        prompt_name="system-prompt",
                        variables={"company_name": "Allianz"},
                    )
                ],
            ),
            models=ModelConfig(default="gpt-4o", per_agent={"classifier": "gpt-4o-mini"}),
            budget=BudgetConfig(monthly_usd=500.0, per_run_usd=0.15),
            sla=SLAConfig(target_seconds=5, p95_target_seconds=8),
            routing=RoutingConfig(queue_name="azhu-rag-queue"),
        )
        assert config.display_name == "AZHU ASZF Chatbot"
        assert len(config.data_sources.collections) == 1
        assert config.budget.monthly_usd == 500.0
        assert config.routing.queue_name == "azhu-rag-queue"

    def test_with_intents(self) -> None:
        config = InstanceConfig(
            instance_name="email-intent",
            skill_template="email_intent_processor",
            customer="azhu",
            prompts=PromptConfig(namespace="azhu/email"),
            intents=[
                IntentConfig(name="claim", handler="extract_claim", priority=1),
                IntentConfig(name="status", handler="lookup_status", auto_respond=True),
            ],
        )
        assert len(config.intents) == 2
        assert config.intents[1].auto_respond is True

    def test_missing_required_fields_raises(self) -> None:
        with pytest.raises(Exception):
            InstanceConfig()  # type: ignore[call-arg]

    def test_disabled_instance(self) -> None:
        config = InstanceConfig(
            instance_name="disabled-test",
            skill_template="test_skill",
            customer="testco",
            enabled=False,
            prompts=PromptConfig(namespace="testco/test"),
        )
        assert config.enabled is False
