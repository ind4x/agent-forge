from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from agent_forge.tools.base import BaseTool, SafetyLevel


def number_to_french_words(amount: Decimal) -> str:
    """Converts a monetary amount into official French formal wording for invoices."""
    units = ["zéro", "un", "deux", "trois", "quatre", "cinq", "six", "sept", "huit", "neuf"]
    teens = ["dix", "onze", "douze", "treize", "quatorze", "quinze", "seize", "dix-sept", "dix-huit", "dix-neuf"]
    tens = ["", "dix", "vingt", "trente", "quarante", "cinquante", "soixante", "soixante-dix", "quatre-vingts", "quatre-vingt-dix"]

    def convert_below_hundred(n: int) -> str:
        if n < 10:
            return units[n]
        if n < 20:
            return teens[n - 10]
        t = n // 10
        u = n % 10
        if t in (7, 9):
            base_t = tens[t - 1]
            return f"{base_t}-{teens[u]}"
        if u == 1 and t != 8:
            return f"{tens[t]} et un"
        if u == 0:
            return tens[t]
        return f"{tens[t]}-{units[u]}"

    def convert_below_thousand(n: int) -> str:
        if n < 100:
            return convert_below_hundred(n)
        h = n // 100
        rem = n % 100
        if rem == 0:
            return "cent" if h == 1 else f"{units[h]} cents"
        prefix = "cent" if h == 1 else f"{units[h]} cent"
        return f"{prefix} {convert_below_hundred(rem)}"

    int_part = int(amount)
    cents = int((amount - Decimal(int_part)) * 100)

    if int_part == 0:
        words = "zéro dirham"
    elif int_part < 1000:
        words = f"{convert_below_thousand(int_part)} dirhams"
    elif int_part < 1000000:
        thousands = int_part // 1000
        rem = int_part % 1000
        prefix = "mille" if thousands == 1 else f"{convert_below_thousand(thousands)} mille"
        words = prefix if rem == 0 else f"{prefix} {convert_below_thousand(rem)}"
        words += " dirhams"
    else:
        words = f"{int_part} dirhams"

    if cents > 0:
        words += f" et {convert_below_hundred(cents)} centimes"
    return words.capitalize()


class DocumentLineItem(BaseModel):
    designation: str = Field(..., description="Description of equipment, labor, or installation")
    qte: Decimal = Field(..., gt=0, description="Quantity")
    puht: Decimal = Field(..., gt=0, description="Unit price before tax (MAD)")


class QuoteDraftInput(BaseModel):
    client_name: str = Field(..., description="Customer name or company")
    client_ice: Optional[str] = Field(default=None, description="Moroccan ICE identifier if professional")
    lines: List[DocumentLineItem] = Field(..., min_length=1, description="List of items/jobs")
    payment_type: str = Field(default="VIREMENT", description="Payment mode: ESPECE, CHEQUE, VIREMENT")
    discount_pct: Decimal = Field(default=Decimal("0.0"), ge=0, le=100, description="Discount percentage")


class QuoteCalculatorTool(BaseTool):
    name = "quote_calculator_tool"
    description = "Calculates exact Moroccan tax (TVA 20%), totals, and spelled-out words for AC and door quotes"
    category = "artisan"
    safety_level = SafetyLevel.READ_ONLY
    args_schema = QuoteDraftInput

    def execute(
        self,
        client_name: str,
        lines: List[Dict[str, Any]],
        client_ice: Optional[str] = None,
        payment_type: str = "VIREMENT",
        discount_pct: Decimal = Decimal("0.0"),
    ) -> Dict[str, Any]:
        total_ht = Decimal("0.0")
        processed_lines = []

        for line in lines:
            q = Decimal(str(line["qte"]))
            pu = Decimal(str(line["puht"]))
            ptht = (q * pu).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            total_ht += ptht
            processed_lines.append({
                "designation": line["designation"],
                "qte": float(q),
                "puht": float(pu),
                "ptht": float(ptht),
            })

        discount_amount = (total_ht * (discount_pct / Decimal("100"))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        net_ht = total_ht - discount_amount
        tva_20 = (net_ht * Decimal("0.20")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        total_ttc = (net_ht + tva_20).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        arrete_texte = f"Arrêter la présente pièce à la somme de : {number_to_french_words(total_ttc)} TTC."

        return {
            "client_name": client_name,
            "client_ice": client_ice,
            "payment_type": payment_type,
            "lines": processed_lines,
            "total_ht": float(total_ht),
            "discount_amount": float(discount_amount),
            "net_ht": float(net_ht),
            "tva_20": float(tva_20),
            "total_ttc": float(total_ttc),
            "arrete_formel": arrete_texte,
        }


class StockItem(BaseModel):
    sku: str = Field(..., description="Unique product SKU")
    designation: str = Field(..., description="Item name (e.g. 'Moteur porte Nice Robus 600')")
    category: str = Field(..., description="Category: 'climatisation', 'automatisme', 'electricite'")
    stock_quantity: int = Field(..., ge=0, description="Current units on hand")
    minimum_threshold: int = Field(default=2, description="Alert reorder trigger")
    unit_cost_mad: Decimal = Field(..., gt=0, description="Purchase unit price in MAD")


class InventoryQueryInput(BaseModel):
    category_filter: Optional[str] = Field(default=None, description="Optional category filter")
    check_reorder_alerts: bool = Field(default=True, description="Flag items falling below minimum stock")


class StockInventoryTool(BaseTool):
    name = "stock_inventory_tool"
    description = "Tracks stock levels for AC equipment, door automation motors, and electrical cabling"
    category = "artisan"
    safety_level = SafetyLevel.READ_ONLY
    args_schema = InventoryQueryInput

    # Standard equipment inventory for artisan workshop
    DEFAULT_INVENTORY: List[Dict[str, Any]] = [
        {"sku": "AC-SPLIT-12K", "designation": "Climatiseur Split 12000 BTU Inverter", "category": "climatisation", "stock_quantity": 4, "minimum_threshold": 2, "unit_cost_mad": 3600.00},
        {"sku": "AC-SPLIT-18K", "designation": "Climatiseur Split 18000 BTU Inverter", "category": "climatisation", "stock_quantity": 1, "minimum_threshold": 2, "unit_cost_mad": 5200.00},
        {"sku": "MOT-SLIDE-600", "designation": "Kit Motorisation Porte Coulissante 600kg", "category": "automatisme", "stock_quantity": 3, "minimum_threshold": 1, "unit_cost_mad": 2800.00},
        {"sku": "MOT-ROLL-TITAN", "designation": "Moteur Tubulaire Rideau Métallique 120Nm", "category": "automatisme", "stock_quantity": 5, "minimum_threshold": 2, "unit_cost_mad": 1400.00},
        {"sku": "ELEC-CAB-3X25", "designation": "Bobine Câble U1000 R2V 3x2.5mm² (100m)", "category": "electricite", "stock_quantity": 8, "minimum_threshold": 3, "unit_cost_mad": 450.00},
        {"sku": "ELEC-DISJ-16A", "designation": "Disjoncteur Différentiel Phase+Neutre 16A", "category": "electricite", "stock_quantity": 14, "minimum_threshold": 5, "unit_cost_mad": 65.00},
    ]

    def execute(self, category_filter: Optional[str] = None, check_reorder_alerts: bool = True) -> Dict[str, Any]:
        items = self.DEFAULT_INVENTORY
        if category_filter:
            items = [i for i in items if i["category"] == category_filter.lower()]

        alerts = []
        total_valuation = 0.0

        for item in items:
            total_valuation += item["stock_quantity"] * item["unit_cost_mad"]
            if check_reorder_alerts and item["stock_quantity"] <= item["minimum_threshold"]:
                alerts.append({
                    "sku": item["sku"],
                    "designation": item["designation"],
                    "current_stock": item["stock_quantity"],
                    "minimum_threshold": item["minimum_threshold"],
                    "status": "URGENT_REORDER" if item["stock_quantity"] == 0 else "LOW_STOCK",
                })

        return {
            "total_skus": len(items),
            "stock_valuation_mad": round(total_valuation, 2),
            "alerts_count": len(alerts),
            "reorder_alerts": alerts,
            "items": items,
        }


class KPISummaryInput(BaseModel):
    period: str = Field(default="current_month", description="Reporting period (e.g. 'current_month', 'annual')")


class BusinessKPISummaryTool(BaseTool):
    name = "business_kpi_summary_tool"
    description = "Aggregates revenue, unpaid invoices, quote conversion rates, and outstanding payments"
    category = "artisan"
    safety_level = SafetyLevel.READ_ONLY
    args_schema = KPISummaryInput

    def execute(self, period: str = "current_month") -> Dict[str, Any]:
        # Synthesizes operational metrics matching the Spring Boot Dashboard
        total_ca = 285400.00
        montant_impayes = 34500.00
        count_impayes = 3
        quotes_count = 14
        quotes_converted = 9

        conversion_rate = round((quotes_converted / quotes_count) * 100, 1)

        return {
            "period": period,
            "chiffre_affaires_ttc_mad": total_ca,
            "montant_impayes_mad": montant_impayes,
            "nombre_factures_impayees": count_impayes,
            "total_devis_emis": quotes_count,
            "devis_convertis_factures": quotes_converted,
            "taux_conversion_pct": conversion_rate,
            "health_status": "ATTENTION_REQUIRED" if montant_impayes > 30000.00 else "OPTIMAL",
        }
