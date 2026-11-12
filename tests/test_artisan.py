from decimal import Decimal
from agent_forge.tools.packs.artisan import (
    QuoteCalculatorTool,
    StockInventoryTool,
    BusinessKPISummaryTool,
    number_to_french_words,
)


def test_french_number_converter():
    assert number_to_french_words(Decimal("100.00")) == "Cent dirhams"
    assert number_to_french_words(Decimal("1250.50")) == "Mille deux cent cinquante dirhams et cinquante centimes"


def test_quote_calculator():
    tool = QuoteCalculatorTool()
    res = tool.run(
        client_name="Cabinet Dentaire Dr. Alami",
        client_ice="002345678000091",
        payment_type="VIREMENT",
        lines=[
            {"designation": "Fourniture et pose Climatiseur 12000 BTU Inverter", "qte": 2, "puht": 4200.00},
            {"designation": "Liaison frigorifique cuivre et goulottes (10m)", "qte": 1, "puht": 800.00},
        ],
        discount_pct=Decimal("0.0"),
    )
    assert res.success is True
    data = res.output
    # total ht = 2*4200 + 800 = 9200
    assert data["total_ht"] == 9200.00
    # tva 20% = 1840.00
    assert data["tva_20"] == 1840.00
    # total ttc = 11040.00
    assert data["total_ttc"] == 11040.00
    assert "onze mille quarante dirhams" in data["arrete_formel"].lower()


def test_stock_inventory_tool():
    tool = StockInventoryTool()
    res = tool.run(category_filter="climatisation")
    assert res.success is True
    data = res.output
    assert data["total_skus"] == 2
    assert data["stock_valuation_mad"] > 0
    # AC-SPLIT-18K has stock 1 <= minimum threshold 2, so it triggers reorder alert
    assert any(alert["sku"] == "AC-SPLIT-18K" for alert in data["reorder_alerts"])


def test_business_kpi_summary():
    tool = BusinessKPISummaryTool()
    res = tool.run(period="current_month")
    assert res.success is True
    assert res.output["chiffre_affaires_ttc_mad"] > 0
    assert res.output["taux_conversion_pct"] > 50.0
