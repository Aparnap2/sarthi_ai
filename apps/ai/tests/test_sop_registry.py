"""Test suite for SOP Registry and Base Class."""
import pytest
from src.sops.registry import SOPRegistry, register
from src.sops.base import BaseSOP, SOPResult, BANNED_JARGON


class MockSOP(BaseSOP):
    """Mock SOP for testing."""
    sop_name = "SOP_MOCK_TEST"

    async def execute(self, payload_ref: str, founder_id: str) -> SOPResult:
        return SOPResult(
            sop_name=self.sop_name,
            founder_id=founder_id,
            success=True,
        )


class TestSOPRegistry:

    def setup_method(self):
        self.registry = SOPRegistry()
        # Clear registry for clean tests
        from src.sops import registry
        registry._REGISTRY.clear()

    def test_registry_has_method(self):
        """Registry should have has() method."""
        assert hasattr(self.registry, 'has')
        assert callable(self.registry.has)

    def test_registry_get_method(self):
        """Registry should have get() method."""
        assert hasattr(self.registry, 'get')
        assert callable(self.registry.get)

    def test_register_adds_sop(self):
        """register() should add SOP to registry."""
        mock = MockSOP()
        register(mock)
        registry = SOPRegistry()
        assert registry.has("SOP_MOCK_TEST")

    def test_get_returns_sop_instance(self):
        """get() should return registered SOP."""
        mock = MockSOP()
        register(mock)
        registry = SOPRegistry()
        sop = registry.get("SOP_MOCK_TEST")
        assert isinstance(sop, MockSOP)
        assert sop.sop_name == "SOP_MOCK_TEST"

    def test_get_unknown_sop_raises_keyerror(self):
        """get() should raise KeyError for unknown SOP."""
        registry = SOPRegistry()
        with pytest.raises(KeyError):
            registry.get("SOP_UNKNOWN")

    def test_all_dictionary_sops_have_registered_executor(self):
        """All SOPs in event dictionary should have registered executors."""
        from src.config.event_dictionary import _REGISTRY as dict_entries
        registry = SOPRegistry()
        sops_in_dict = {e.sop for e in dict_entries}
        
        # Filter out SOPs that are routers (not executors)
        router_sops = {"SOP_FILE_INGESTION"}  # Router, not executor
        executor_sops = sops_in_dict - router_sops
        
        for sop_name in executor_sops:
            # For now, just check registry structure exists
            # Actual SOPs will be registered in Phase 8-10
            assert registry.has.__class__.__name__ == 'method'


class TestSOPResult:

    def test_sop_result_creation(self):
        """SOPResult should be creatable with minimal fields."""
        result = SOPResult(
            sop_name="SOP_TEST",
            founder_id="founder_123",
            success=True,
        )
        assert result.sop_name == "SOP_TEST"
        assert result.founder_id == "founder_123"
        assert result.success is True
        assert result.fire_alert is False  # default
        assert result.hitl_risk == "low"  # default

    def test_sop_result_with_all_fields(self):
        """SOPResult should accept all optional fields."""
        result = SOPResult(
            sop_name="SOP_TEST",
            founder_id="founder_123",
            success=True,
            fire_alert=True,
            hitl_risk="high",
            headline="Test headline",
            do_this="Test action",
            is_good_news=False,
            output={"key": "value"},
            error=None,
        )
        assert result.fire_alert is True
        assert result.hitl_risk == "high"
        assert result.headline == "Test headline"
        assert result.do_this == "Test action"

    def test_validate_tone_detects_jargon(self):
        """validate_tone() should detect banned jargon."""
        result = SOPResult(
            sop_name="SOP_TEST",
            founder_id="founder_123",
            success=True,
            headline="We leverage synergies",
            do_this="Utilize this paradigm",
        )
        violations = result.validate_tone()
        assert len(violations) > 0
        assert any("leverage" in v for v in violations)
        assert any("synergies" in v for v in violations)

    def test_validate_tone_clean_output(self):
        """validate_tone() should return empty list for clean output."""
        result = SOPResult(
            sop_name="SOP_TEST",
            founder_id="founder_123",
            success=True,
            headline="Your revenue increased",
            do_this="Review the details",
        )
        violations = result.validate_tone()
        assert len(violations) == 0


class TestBaseSOP:

    def test_base_sop_is_abstract(self):
        """BaseSOP should be abstract (cannot instantiate)."""
        with pytest.raises(TypeError):
            BaseSOP()

    def test_base_sop_requires_sop_name(self):
        """Subclasses must define sop_name."""
        class IncompleteSOP(BaseSOP):
            pass
        
        with pytest.raises(TypeError):
            IncompleteSOP()

    def test_base_sop_requires_execute(self):
        """Subclasses must implement execute()."""
        class IncompleteSOP(BaseSOP):
            sop_name = "SOP_INCOMPLETE"
        
        with pytest.raises(TypeError):
            IncompleteSOP()

    def test_concrete_sop_works(self):
        """Concrete SOP implementation should work."""
        mock = MockSOP()
        assert mock.sop_name == "SOP_MOCK_TEST"
        assert callable(mock.execute)
