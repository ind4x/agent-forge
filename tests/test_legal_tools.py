import pytest
from decimal import Decimal
import datetime
from agent_forge.tools.packs.legal import (
    LegalConflictCheckerTool,
    ProceduralDeadlineCalculatorTool,
    CaseDossierLookupTool,
    LegalCodeRAGSearchTool,
    FeeConventionGeneratorTool,
)


def test_legal_conflict_checker():
    tool = LegalConflictCheckerTool()

    # 1. Prospect without conflict
    res1 = tool.run(prospect_name="Société Nouvelle Tanger", adverse_party="Entreprise Inconnue")
    assert res1.success is True
    assert res1.output["conflict_detected"] is False
    assert res1.output["clearance_status"] == "VALIDE_SANS_CONFLIT"

    # 2. Prospect who is adversary in an active case (Consorts Benjelloun)
    res2 = tool.run(prospect_name="Consorts Benjelloun", matter_subject="Nouveau litige")
    assert res2.success is True
    assert res2.output["conflict_detected"] is True
    assert res2.output["clearance_status"] == "CONFLIT_BLOQUANT"


def test_procedural_deadline_calculator():
    tool = ProceduralDeadlineCalculatorTool()
    # Compute 10 days in the future
    future_date = (datetime.date.today() + datetime.timedelta(days=10)).isoformat()
    res = tool.run(hearing_date_str=future_date, jurisdiction="Tribunal de Commerce")
    assert res.success is True
    assert res.output["days_until_hearing"] == 10
    assert len(res.output["schedule"]) == 4


def test_case_dossier_lookup():
    tool = CaseDossierLookupTool()
    # Lookup by client name
    res = tool.run(query="Société Foncière Anfa")
    assert res.success is True
    assert res.output["found"] is True
    assert res.output["count"] >= 1
    assert res.output["dossiers"][0]["ref"] == "DOS-2026-042"


def test_legal_code_rag_search():
    tool = LegalCodeRAGSearchTool()
    res = tool.run(query="résiliation bail commercial loyers")
    assert res.success is True
    assert res.output["matches_count"] >= 1
    assert "Loi 49-16" in res.output["results"][0]["source"]


def test_fee_convention_generator():
    tool = FeeConventionGeneratorTool()
    res = tool.run(
        client_name="Société Foncière Anfa",
        case_description="Recouvrement loyers impayés",
        billing_mode="FORFAIT",
        amount_mad=Decimal("30000.00"),
        success_fee_pct=Decimal("10.0"),
    )
    assert res.success is True
    assert res.output["total_ttc_mad"] == 33000.00  # 10% legal VAT
    assert res.output["status"] == "PROJET_CONVENTION_PRET"
