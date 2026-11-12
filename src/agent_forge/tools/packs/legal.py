from decimal import Decimal
import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from agent_forge.tools.base import BaseTool, SafetyLevel


class ConflictCheckInput(BaseModel):
    prospect_name: str = Field(..., description="Nom de la personne physique ou morale demanderesse")
    adverse_party: Optional[str] = Field(None, description="Nom de la partie adverse déclarée")
    matter_subject: Optional[str] = Field(None, description="Objet sommaire du litige ou du conseil")


class LegalConflictCheckerTool(BaseTool):
    name = "legal_conflict_checker"
    description = "Vérifie les antécédents et conflits d'intérêts déontologiques (partie adverse vs clients actuels/passés)"
    category = "legal"
    safety_level = SafetyLevel.READ_ONLY
    args_schema = ConflictCheckInput

    # In-memory registry of existing cases and representations
    MOCK_REPRESENTATIONS = [
        {"client": "Société Foncière Anfa", "adverse": "Consorts Benjelloun", "matter": "Bail commercial"},
        {"client": "Banque Maghrébine", "adverse": "Omnium Industriel", "matter": "Recouvrement créance"},
        {"client": "Groupe El Alami", "adverse": "M. Karim Tazi", "matter": "Litige prud'homal"},
    ]

    def execute(self, prospect_name: str, adverse_party: Optional[str] = None, matter_subject: Optional[str] = None) -> Dict[str, Any]:
        prospect_clean = prospect_name.lower().strip()
        adverse_clean = (adverse_party or "").lower().strip()

        conflicts = []
        # Check if prospect is adverse in an existing active representation
        for rep in self.MOCK_REPRESENTATIONS:
            if prospect_clean in rep["adverse"].lower():
                conflicts.append({
                    "conflict_type": "PROSPECT_EST_PARTIE_ADVERSE",
                    "existing_client": rep["client"],
                    "adverse_party": rep["adverse"],
                    "matter": rep["matter"],
                    "verdict": "REFUS_MANDAT_OBLIGATOIRE",
                })
            # Check if declared adverse party is an existing client of the firm
            if adverse_clean and adverse_clean in rep["client"].lower():
                conflicts.append({
                    "conflict_type": "ADVERSE_EST_CLIENT_ACTUEL",
                    "existing_client": rep["client"],
                    "adverse_party": adverse_party,
                    "matter": rep["matter"],
                    "verdict": "CONFLIT_DIRECT_INCOMPATIBLE",
                })

        has_conflict = len(conflicts) > 0
        return {
            "prospect": prospect_name,
            "adverse_party": adverse_party,
            "conflict_detected": has_conflict,
            "details": conflicts if has_conflict else "Aucun conflit d'intérêts répertorié. Mandat admissible sous réserve de déontologie.",
            "clearance_status": "CONFLIT_BLOQUANT" if has_conflict else "VALIDE_SANS_CONFLIT",
        }


class ProceduralDeadlineInput(BaseModel):
    hearing_date_str: str = Field(..., description="Date de la prochaine audience (format YYYY-MM-DD)")
    jurisdiction: str = Field(default="Tribunal de Commerce", description="Juridiction compétente")
    case_reference: Optional[str] = Field(None, description="Numéro de rôle ou référence du dossier")


class ProceduralDeadlineCalculatorTool(BaseTool):
    name = "procedural_deadline_calculator"
    description = "Calcule les délais de procédure judiciaires (J-15 conclusions, J-7 pièces, J-1 vérification chemise)"
    category = "legal"
    safety_level = SafetyLevel.READ_ONLY
    args_schema = ProceduralDeadlineInput

    def execute(self, hearing_date_str: str, jurisdiction: str = "Tribunal de Commerce", case_reference: Optional[str] = None) -> Dict[str, Any]:
        try:
            hearing_date = datetime.date.fromisoformat(hearing_date_str)
        except ValueError:
            return {"error": f"Format de date invalide: {hearing_date_str}. Utiliser YYYY-MM-DD."}

        today = datetime.date.today()
        days_remaining = (hearing_date - today).days

        deadline_conclusions = hearing_date - datetime.timedelta(days=15)
        deadline_pieces = hearing_date - datetime.timedelta(days=7)
        deadline_alerte_avocat = hearing_date - datetime.timedelta(days=1)

        return {
            "hearing_date": str(hearing_date),
            "jurisdiction": jurisdiction,
            "case_reference": case_reference or "N/A",
            "days_until_hearing": days_remaining,
            "schedule": [
                {"step": "Notification conclusions adverses", "deadline": str(deadline_conclusions), "status": "ECHU" if today > deadline_conclusions else "EN_ATTENTE"},
                {"step": "Bordereau communication de pièces", "deadline": str(deadline_pieces), "status": "ECHU" if today > deadline_pieces else "EN_ATTENTE"},
                {"step": "Synthèse et chemise de plaidoirie", "deadline": str(deadline_alerte_avocat), "status": "ECHU" if today > deadline_alerte_avocat else "EN_ATTENTE"},
                {"step": "Audience de plaidoirie", "deadline": str(hearing_date), "status": "PASSE" if today > hearing_date else "IMMINENTE" if days_remaining <= 3 else "PROGRAMMEE"}
            ],
            "urgency": "CRITIQUE_J_MOINS_3" if 0 <= days_remaining <= 3 else "STANDARD"
        }


class CaseDossierLookupInput(BaseModel):
    query: str = Field(..., description="Nom du client, partie adverse ou numéro de rôle")


class CaseDossierLookupTool(BaseTool):
    name = "case_dossier_lookup"
    description = "Recherche sémantique et extraction des fiches de dossiers judiciaires actifs et archivés"
    category = "legal"
    safety_level = SafetyLevel.READ_ONLY
    args_schema = CaseDossierLookupInput

    MOCK_DOSSIERS = [
        {
            "ref": "DOS-2026-042",
            "client": "Société Foncière Anfa",
            "adverse": "Consorts Benjelloun",
            "avocat_adverse": "Me. Kettani (Barreau de Casablanca)",
            "jurisdiction": "Tribunal de Commerce de Casablanca",
            "chambre": "3ème Chambre Commerciale",
            "objet": "Résiliation de bail commercial pour défaut de paiement et indemnité d'occupation",
            "statut": "MISE_EN_DELIBERE",
            "prochaine_audience": "2026-11-24",
            "montant_litige_mad": 680000.00,
            "honoraires_factures_mad": 45000.00,
            "pieces_deposees": 14,
            "derniere_conclusions": "Conclusions responsives déposées le 12/10/2026",
        },
        {
            "ref": "DOS-2026-058",
            "client": "M. Taha Berrada",
            "adverse": "Compagnie d'Assurances Al Watanya",
            "avocat_adverse": "Me. Belhadj (Barreau de Rabat)",
            "jurisdiction": "Tribunal de Première Instance de Casablanca",
            "chambre": "Chambre Civile / Accidents",
            "objet": "Indemnisation corporelle suite à accident de la circulation",
            "statut": "EXPERTISE_MEDICALE",
            "prochaine_audience": "2026-12-08",
            "montant_litige_mad": 320000.00,
            "honoraires_factures_mad": 25000.00,
            "pieces_deposees": 8,
            "derniere_conclusions": "Rapport préliminaire d'expertise déposé au greffe",
        },
        {
            "ref": "DOS-2026-061",
            "client": "Société BTP Atlas SARL",
            "adverse": "SNC Travaux du Sud",
            "avocat_adverse": "Me. Naciri (Barreau de Marrakech)",
            "jurisdiction": "Tribunal de Commerce de Marrakech",
            "chambre": "Chambre des Référés",
            "objet": "Référé provision sur situation de travaux impayée",
            "statut": "PLAIDOIRIE_IMMINENTE",
            "prochaine_audience": "2026-11-18",
            "montant_litige_mad": 450000.00,
            "honoraires_factures_mad": 30000.00,
            "pieces_deposees": 19,
            "derniere_conclusions": "Bordereau de 19 pièces notifié à confrère le 05/11/2026",
        },
    ]

    def execute(self, query: str) -> Dict[str, Any]:
        q = query.lower().strip()
        matches = []
        for d in self.MOCK_DOSSIERS:
            searchable = f"{d['ref']} {d['client']} {d['adverse']} {d['objet']}".lower()
            if q in searchable:
                matches.append(d)

        if not matches:
            # Fallback returns all active matters summary
            return {
                "query": query,
                "found": False,
                "total_dossiers_actifs": len(self.MOCK_DOSSIERS),
                "summary": [
                    {"ref": d["ref"], "client": d["client"], "adverse": d["adverse"], "audience": d["prochaine_audience"], "statut": d["statut"]}
                    for d in self.MOCK_DOSSIERS
                ]
            }

        return {
            "query": query,
            "found": True,
            "count": len(matches),
            "dossiers": matches
        }


class LegalCodeSearchInput(BaseModel):
    query: str = Field(..., description="Question de droit, mot-clé juridique ou numéro d'article")
    code_target: Optional[str] = Field("code_commerce", description="Code ciblé (code_commerce, code_procedure_civile, doc)")


class LegalCodeRAGSearchTool(BaseTool):
    name = "legal_code_rag_search"
    description = "Recherche RAG dans les codes juridiques (Code de Commerce, DOC, Procédure Civile) et jurisprudence"
    category = "legal"
    safety_level = SafetyLevel.READ_ONLY
    args_schema = LegalCodeSearchInput

    LEGAL_CORPUS = {
        "bail_commercial": {
            "source": "Loi 49-16 relative aux baux d'immeubles ou de locaux à usage commercial",
            "article": "Article 26 & 27",
            "principe": "Le bailleur ne peut demander la résiliation du bail pour non-paiement des loyers qu'après mise en demeure de payer restée sans effet pendant un délai de 15 jours.",
            "jurisprudence": "Cour de Cassation, arrêt N°412/2021 : La régularisation intégrale dans le délai de 15 jours éteint l'action en résiliation."
        },
        "delai_appel": {
            "source": "Code de Procédure Civile (CPC Marocain)",
            "article": "Article 134",
            "principe": "Le délai pour interjeter appel est de trente jours à compter de la notification du jugement à personne ou à domicile réel ou élu.",
            "jurisprudence": "Délai de rigueur, forclusion encourue d'office par la juridiction d'appel."
        },
        "responsabilite_contractuelle": {
            "source": "Dahir des Obligations et Contrats (D.O.C.)",
            "article": "Article 263 & 264",
            "principe": "Les dommages-intérêts ne sont dus que lorsque le débiteur est en demeure d'exécuter son obligation.",
            "jurisprudence": "Nécessité de prouver la faute, le préjudice direct et certain, et le lien de causalité."
        },
        "conflit_interets": {
            "source": "Loi 28-08 régissant la profession d'avocat & Règlement Intérieur du Barreau",
            "article": "Article 42",
            "principe": "L'avocat ne peut être le défenseur ou le conseil de plus d'une partie dans la même affaire ou d'intérêts opposés. Il lui est interdit de représenter une partie contre un client actuel.",
            "jurisprudence": "Sanction disciplinaire de radiation ou suspension en cas de manquement grave à la loyauté déontologique."
        }
    }

    def execute(self, query: str, code_target: Optional[str] = "code_commerce") -> Dict[str, Any]:
        q = query.lower()
        matched_results = []
        for key, entry in self.LEGAL_CORPUS.items():
            content = f"{key} {entry['source']} {entry['article']} {entry['principe']} {entry['jurisprudence']}".lower()
            if any(term in content for term in q.split() if len(term) > 3):
                matched_results.append(entry)

        if not matched_results:
            matched_results.append(self.LEGAL_CORPUS["conflit_interets"])

        return {
            "query": query,
            "matches_count": len(matched_results),
            "results": matched_results
        }


class FeeConventionInput(BaseModel):
    client_name: str = Field(..., description="Nom du client ou entreprise")
    case_description: str = Field(..., description="Description synthétique du mandat")
    billing_mode: str = Field(default="FORFAIT", description="Mode de facturation: FORFAIT, TAUX_HORAIRE, RESULTAT")
    amount_mad: Decimal = Field(..., gt=0, description="Montant hors taxes (MAD)")
    success_fee_pct: Optional[Decimal] = Field(None, ge=0, le=50, description="Pourcentage d'honoraire de résultat éventuel")


class FeeConventionGeneratorTool(BaseTool):
    name = "fee_convention_generator"
    description = "Génère un projet officiel de convention d'honoraires d'avocat conforme au Barreau"
    category = "legal"
    safety_level = SafetyLevel.MUTATING_SAFE
    args_schema = FeeConventionInput

    def execute(self, client_name: str, case_description: str, billing_mode: str, amount_mad: Decimal, success_fee_pct: Optional[Decimal] = None) -> Dict[str, Any]:
        tva_rate = Decimal("0.10")  # TVA 10% pour les professions juridiques libérales au Maroc
        tva_amount = (amount_mad * tva_rate).quantize(Decimal("0.01"))
        total_ttc = amount_mad + tva_amount

        ref_convention = f"CONV-{datetime.date.today().year}-{datetime.datetime.now().strftime('%m%d%H%M')}"

        clauses = [
            f"Mandat : Assistance et représentation juridique pour : {case_description}",
            f"Honoraires fixes : {amount_mad:,.2f} MAD HT ({total_ttc:,.2f} MAD TTC, TVA 10% incluse)",
            f"Modalités de règlement : 50% à l'ouverture du dossier, solde à la clôture de l'instruction",
        ]
        if success_fee_pct and success_fee_pct > 0:
            clauses.append(f"Honoraire de résultat complémentaire : {success_fee_pct}% du montant obtenu ou économisé")

        return {
            "reference": ref_convention,
            "client": client_name,
            "billing_mode": billing_mode,
            "amount_ht_mad": float(amount_mad),
            "tva_mad": float(tva_amount),
            "total_ttc_mad": float(total_ttc),
            "clauses": clauses,
            "requires_lawyer_signature": True,
            "status": "PROJET_CONVENTION_PRET"
        }
