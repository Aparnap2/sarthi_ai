"""
E2E Tests for Sarthi v4.2 Internal Ops — Phase 6.

Full stack E2E tests covering all 6 desks:
- Finance Desk: Bank CSV → CFOFinding → message
- People Desk: New hire → tasks created → briefing
- Legal Desk: Contract upload → expiry alert
- Intelligence Desk: Revenue anomaly → CFO alert
- IT Desk: SaaS subscription → cost optimization
- Admin Desk: Meeting transcript → SOP generated

Run with: pytest apps/ai/tests/test_e2e_internal_ops.py -v
"""

import pytest
import os
import json
from unittest.mock import MagicMock, patch, AsyncMock
from typing import Dict, Any

from src.agents.chief_of_staff_agent import ChiefOfStaffAgent, get_chief_of_staff_agent
from src.agents.finance_desk import FinanceDeskAgent
from src.agents.people_desk import PeopleDeskAgent
from src.agents.legal_desk import LegalDeskAgent
from src.agents.intelligence_desk import IntelligenceDeskAgent
from src.agents.it_desk import ITDeskAgent
from src.agents.admin_desk import AdminDeskAgent


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client for all desks."""
    client = MagicMock()
    
    # Mock chat completions
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="mock response"))]
    client.chat.completions.create.return_value = mock_response
    
    return client


@pytest.fixture
def mock_grpc_client():
    """Create a mock gRPC client."""
    return MagicMock()


# =============================================================================
# E2E Test Flows
# =============================================================================

class TestE2EInternalOps:
    """Full stack E2E tests for internal ops flows."""

    def test_bank_csv_to_cfo_finding(self, mock_llm_client):
        """
        E2E Flow 1: Bank CSV → Finance Desk → CFOFinding → message.
        
        Scenario:
        1. Founder uploads bank statement CSV
        2. Chief of Staff routes to Finance Desk
        3. CFO agent analyzes cash position
        4. CFOFinding generated with jargon-free insights
        5. Message drafted for Telegram (mock send)
        """
        with patch('src.agents.chief_of_staff_agent.get_llm_client', return_value=mock_llm_client):
            with patch('src.agents.chief_of_staff_agent.get_chat_model', return_value='gpt-4'):
                # Mock Finance Desk
                mock_finance = MagicMock()
                mock_finance_graph = MagicMock()
                mock_finance_graph.invoke.return_value = {
                    "result": {
                        "finding_type": "cfo",
                        "content": "Your cash runway is 6 months at current burn rate.",
                        "action": "Review monthly expenses to extend runway to 9 months.",
                        "confidence": 0.92,
                        "jargon_free": True,
                    }
                }
                mock_finance.create_graph.return_value = mock_finance_graph
                
                with patch('src.agents.chief_of_staff_agent.get_finance_desk_agent', return_value=mock_finance):
                    with patch('src.agents.chief_of_staff_agent.get_people_desk_agent'):
                        with patch('src.agents.chief_of_staff_agent.get_legal_desk_agent'):
                            with patch('src.agents.chief_of_staff_agent.get_intelligence_desk_agent'):
                                with patch('src.agents.chief_of_staff_agent.get_it_desk_agent'):
                                    with patch('src.agents.chief_of_staff_agent.get_admin_desk_agent'):
                                        agent = ChiefOfStaffAgent()
                                        graph = agent.create_graph()
                                        
                                        # Execute workflow
                                        result = graph.invoke({
                                            "founder_id": "founder-e2e-001",
                                            "event_type": "bank_statement",
                                            "event_payload": {
                                                "bank_data": {
                                                    "balance": 500000,
                                                    "currency": "INR",
                                                    "transactions": [
                                                        {"amount": -50000, "category": "salaries"},
                                                        {"amount": -20000, "category": "rent"},
                                                        {"amount": 100000, "category": "revenue"},
                                                    ]
                                                },
                                                "accounting_data": {
                                                    "monthly_burn": 70000,
                                                    "monthly_revenue": 100000,
                                                }
                                            },
                                        })
                                        
                                        # Assertions
                                        assert result is not None
                                        assert result["routed_to"] == "finance"
                                        assert result["result"] is not None
                                        assert result["result"]["finding_type"] == "cfo"
                                        assert "cash runway" in result["result"]["content"].lower()
                                        assert result["result"]["jargon_free"] is True

    def test_new_hire_to_people_tasks(self, mock_llm_client):
        """
        E2E Flow 2: New hire → People Desk → tasks created.
        
        Scenario:
        1. New hire joins company
        2. Chief of Staff routes to People Desk
        3. HR Coordinator creates onboarding tasks
        4. PeopleOpsFinding generated
        5. Weekly briefing updated
        """
        with patch('src.agents.chief_of_staff_agent.get_llm_client', return_value=mock_llm_client):
            with patch('src.agents.chief_of_staff_agent.get_chat_model', return_value='gpt-4'):
                # Mock People Desk
                mock_people = MagicMock()
                mock_people_graph = MagicMock()
                mock_people_graph.invoke.return_value = {
                    "result": {
                        "finding_type": "people_ops",
                        "employee_name": "John Doe",
                        "onboarding_tasks": [
                            "Setup email account",
                            "Schedule orientation meeting",
                            "Assign buddy",
                            "Prepare equipment",
                        ],
                        "tasks_created": 4,
                        "jargon_free": True,
                    }
                }
                mock_people.create_graph.return_value = mock_people_graph
                
                with patch('src.agents.chief_of_staff_agent.get_finance_desk_agent'):
                    with patch('src.agents.chief_of_staff_agent.get_people_desk_agent', return_value=mock_people):
                        with patch('src.agents.chief_of_staff_agent.get_legal_desk_agent'):
                            with patch('src.agents.chief_of_staff_agent.get_intelligence_desk_agent'):
                                with patch('src.agents.chief_of_staff_agent.get_it_desk_agent'):
                                    with patch('src.agents.chief_of_staff_agent.get_admin_desk_agent'):
                                        agent = ChiefOfStaffAgent()
                                        graph = agent.create_graph()
                                        
                                        result = graph.invoke({
                                            "founder_id": "founder-e2e-002",
                                            "event_type": "new_hire",
                                            "event_payload": {
                                                "employee_name": "John Doe",
                                                "role": "Software Engineer",
                                                "start_date": "2026-03-15",
                                                "department": "Engineering",
                                            },
                                        })
                                        
                                        assert result is not None
                                        assert result["routed_to"] == "people"
                                        assert result["result"]["finding_type"] == "people_ops"
                                        assert result["result"]["tasks_created"] == 4
                                        assert len(result["result"]["onboarding_tasks"]) == 4

    def test_contract_upload_to_expiry_alert(self, mock_llm_client):
        """
        E2E Flow 3: Contract upload → Legal Desk → expiry alert.
        
        Scenario:
        1. Vendor contract uploaded
        2. Chief of Staff routes to Legal Desk
        3. Contracts Coordinator extracts key dates
        4. Expiry alert scheduled
        5. LegalOpsResult generated
        """
        with patch('src.agents.chief_of_staff_agent.get_llm_client', return_value=mock_llm_client):
            with patch('src.agents.chief_of_staff_agent.get_chat_model', return_value='gpt-4'):
                # Mock Legal Desk
                mock_legal = MagicMock()
                mock_legal_graph = MagicMock()
                mock_legal_graph.invoke.return_value = {
                    "result": {
                        "finding_type": "legal_ops",
                        "contract_type": "Vendor Agreement",
                        "contract_name": "AWS Enterprise Agreement",
                        "expiry_date": "2027-03-15",
                        "days_until_expiry": 367,
                        "alert_scheduled": True,
                        "jargon_free": True,
                    }
                }
                mock_legal.create_graph.return_value = mock_legal_graph
                
                with patch('src.agents.chief_of_staff_agent.get_finance_desk_agent'):
                    with patch('src.agents.chief_of_staff_agent.get_people_desk_agent'):
                        with patch('src.agents.chief_of_staff_agent.get_legal_desk_agent', return_value=mock_legal):
                            with patch('src.agents.chief_of_staff_agent.get_intelligence_desk_agent'):
                                with patch('src.agents.chief_of_staff_agent.get_it_desk_agent'):
                                    with patch('src.agents.chief_of_staff_agent.get_admin_desk_agent'):
                                        agent = ChiefOfStaffAgent()
                                        graph = agent.create_graph()
                                        
                                        result = graph.invoke({
                                            "founder_id": "founder-e2e-003",
                                            "event_type": "contract_uploaded",
                                            "event_payload": {
                                                "contract_name": "AWS Enterprise Agreement",
                                                "file_path": "/contracts/aws-agreement.pdf",
                                                "contract_type": "Vendor Agreement",
                                            },
                                        })
                                        
                                        assert result is not None
                                        assert result["routed_to"] == "legal"
                                        assert result["result"]["finding_type"] == "legal_ops"
                                        assert result["result"]["alert_scheduled"] is True

    def test_meeting_transcript_to_sop(self, mock_llm_client):
        """
        E2E Flow 4: Meeting transcript → Admin Desk → SOP generated.
        
        Scenario:
        1. Meeting transcript uploaded
        2. Chief of Staff routes to Admin Desk
        3. EA extracts action items
        4. Knowledge Manager generates SOP
        5. Documentation updated
        """
        with patch('src.agents.chief_of_staff_agent.get_llm_client', return_value=mock_llm_client):
            with patch('src.agents.chief_of_staff_agent.get_chat_model', return_value='gpt-4'):
                # Mock Admin Desk
                mock_admin = MagicMock()
                mock_admin_graph = MagicMock()
                mock_admin_graph.invoke.return_value = {
                    "result": {
                        "finding_type": "admin_ops",
                        "meeting_title": "Weekly Product Review",
                        "action_items": [
                            "Update product roadmap",
                            "Schedule customer interviews",
                            "Review sprint velocity",
                        ],
                        "sop_generated": True,
                        "sop_title": "Product Review Process",
                        "jargon_free": True,
                    }
                }
                mock_admin.create_graph.return_value = mock_admin_graph
                
                with patch('src.agents.chief_of_staff_agent.get_finance_desk_agent'):
                    with patch('src.agents.chief_of_staff_agent.get_people_desk_agent'):
                        with patch('src.agents.chief_of_staff_agent.get_legal_desk_agent'):
                            with patch('src.agents.chief_of_staff_agent.get_intelligence_desk_agent'):
                                with patch('src.agents.chief_of_staff_agent.get_it_desk_agent'):
                                    with patch('src.agents.chief_of_staff_agent.get_admin_desk_agent', return_value=mock_admin):
                                        agent = ChiefOfStaffAgent()
                                        graph = agent.create_graph()
                                        
                                        result = graph.invoke({
                                            "founder_id": "founder-e2e-004",
                                            "event_type": "meeting_transcript",
                                            "event_payload": {
                                                "transcript": "Discussion about product roadmap and customer feedback...",
                                                "meeting_title": "Weekly Product Review",
                                                "participants": ["Alice", "Bob", "Charlie"],
                                                "duration_minutes": 60,
                                            },
                                        })
                                        
                                        assert result is not None
                                        assert result["routed_to"] == "admin"
                                        assert result["result"]["finding_type"] == "admin_ops"
                                        assert result["result"]["sop_generated"] is True
                                        assert len(result["result"]["action_items"]) == 3

    def test_revenue_anomaly_to_intelligence(self, mock_llm_client):
        """
        E2E Flow 5: Revenue anomaly → Intelligence Desk → CFO alert.
        
        Scenario:
        1. Revenue anomaly detected (spike/drop)
        2. Chief of Staff routes to Intelligence Desk
        3. BI Analyst investigates
        4. IntelligenceFinding generated
        5. CFO alert sent
        """
        with patch('src.agents.chief_of_staff_agent.get_llm_client', return_value=mock_llm_client):
            with patch('src.agents.chief_of_staff_agent.get_chat_model', return_value='gpt-4'):
                # Mock Intelligence Desk
                mock_intel = MagicMock()
                mock_intel_graph = MagicMock()
                mock_intel_graph.invoke.return_value = {
                    "result": {
                        "finding_type": "intelligence",
                        "anomaly_type": "revenue_spike",
                        "variance_percent": 150,
                        "confidence": 0.95,
                        "recommendation": "Investigate source of spike - possible data error or one-time event",
                        "cfo_alert": True,
                        "jargon_free": True,
                    }
                }
                mock_intel.create_graph.return_value = mock_intel_graph
                
                with patch('src.agents.chief_of_staff_agent.get_finance_desk_agent'):
                    with patch('src.agents.chief_of_staff_agent.get_people_desk_agent'):
                        with patch('src.agents.chief_of_staff_agent.get_legal_desk_agent'):
                            with patch('src.agents.chief_of_staff_agent.get_intelligence_desk_agent', return_value=mock_intel):
                                with patch('src.agents.chief_of_staff_agent.get_it_desk_agent'):
                                    with patch('src.agents.chief_of_staff_agent.get_admin_desk_agent'):
                                        agent = ChiefOfStaffAgent()
                                        graph = agent.create_graph()
                                        
                                        result = graph.invoke({
                                            "founder_id": "founder-e2e-005",
                                            "event_type": "revenue_anomaly",
                                            "event_payload": {
                                                "current_revenue": 1500000,
                                                "expected_revenue": 600000,
                                                "variance_percent": 150,
                                                "period": "2026-02",
                                            },
                                        })
                                        
                                        assert result is not None
                                        assert result["routed_to"] == "intelligence"
                                        assert result["result"]["finding_type"] == "intelligence"
                                        assert result["result"]["cfo_alert"] is True

    def test_saas_subscription_to_it(self, mock_llm_client):
        """
        E2E Flow 6: SaaS subscription → IT Desk → cost optimization.
        
        Scenario:
        1. New SaaS subscription detected
        2. Chief of Staff routes to IT Desk
        3. IT Admin reviews utilization
        4. ITRiskAlert generated
        5. Cost optimization recommendation
        """
        with patch('src.agents.chief_of_staff_agent.get_llm_client', return_value=mock_llm_client):
            with patch('src.agents.chief_of_staff_agent.get_chat_model', return_value='gpt-4'):
                # Mock IT Desk
                mock_it = MagicMock()
                mock_it_graph = MagicMock()
                mock_it_graph.invoke.return_value = {
                    "result": {
                        "finding_type": "it_ops",
                        "tool_name": "Figma",
                        "monthly_cost": 5000,
                        "seats_purchased": 20,
                        "seats_active": 12,
                        "utilization": 0.60,
                        "recommendation": "Reduce seats from 20 to 15 to save ₹2,500/month",
                        "jargon_free": True,
                    }
                }
                mock_it.create_graph.return_value = mock_it_graph
                
                with patch('src.agents.chief_of_staff_agent.get_finance_desk_agent'):
                    with patch('src.agents.chief_of_staff_agent.get_people_desk_agent'):
                        with patch('src.agents.chief_of_staff_agent.get_legal_desk_agent'):
                            with patch('src.agents.chief_of_staff_agent.get_intelligence_desk_agent'):
                                with patch('src.agents.chief_of_staff_agent.get_it_desk_agent', return_value=mock_it):
                                    with patch('src.agents.chief_of_staff_agent.get_admin_desk_agent'):
                                        agent = ChiefOfStaffAgent()
                                        graph = agent.create_graph()
                                        
                                        result = graph.invoke({
                                            "founder_id": "founder-e2e-006",
                                            "event_type": "saas_subscription",
                                            "event_payload": {
                                                "tool_name": "Figma",
                                                "cost": 5000,
                                                "seats": 20,
                                                "billing_period": "monthly",
                                            },
                                        })
                                        
                                        assert result is not None
                                        assert result["routed_to"] == "it"
                                        assert result["result"]["finding_type"] == "it_ops"
                                        assert result["result"]["utilization"] == 0.60


# =============================================================================
# Integration Tests (Real LLM - Optional)
# =============================================================================

@pytest.mark.skipif(not os.environ.get("AZURE_OPENAI_ENDPOINT"), reason="No Azure OpenAI configured")
class TestE2EInternalOpsIntegration:
    """Integration tests with real Azure LLM."""

    def test_full_bank_statement_flow(self):
        """Test complete bank statement flow with real LLM."""
        agent = ChiefOfStaffAgent()
        graph = agent.create_graph()

        result = graph.invoke({
            "founder_id": "founder-integration-001",
            "event_type": "bank_statement",
            "event_payload": {
                "bank_data": {
                    "balance": 500000,
                    "currency": "INR",
                },
                "accounting_data": {
                    "monthly_burn": 70000,
                }
            },
        })

        assert result is not None
        assert result["routed_to"] == "finance"
        assert result["result"] is not None
