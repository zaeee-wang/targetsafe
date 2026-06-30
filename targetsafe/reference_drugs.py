from __future__ import annotations

from copy import deepcopy
from typing import Any

from targetsafe.chem import mol_svg_data_uri, tanimoto_like_similarity


REFERENCE_EGFR_DRUGS: list[dict[str, Any]] = [
    {
        "drug_id": "gefitinib",
        "name": "Gefitinib",
        "smiles": "COc1cc2ncnc(Nc3ccc(F)c(Cl)c3)c2cc1OCCCN1CCOCC1",
        "pubchem_cid": "123631",
        "chembl_id": "CHEMBL939",
        "context": "First-generation EGFR tyrosine kinase inhibitor reference for EGFR-mutant NSCLC.",
        "activity_evidence": "Reference EGFR inhibitor scaffold used as an offline positive-control context.",
        "label_risk_context": [
            "Diarrhea, rash, acneiform dermatitis, dry skin, and nausea are common EGFR TKI adverse reaction review topics.",
            "Interstitial lung disease or pneumonitis is a serious class-level label review topic.",
            "Hepatic toxicity monitoring is relevant for EGFR TKI label review.",
        ],
        "evidence_source": "Offline reference library; refresh PubChem, ChEMBL, and openFDA when live APIs are enabled.",
        "source_status": "fallback_reference",
    },
    {
        "drug_id": "erlotinib",
        "name": "Erlotinib",
        "smiles": "C#Cc1cccc(Nc2ncnc3cc(OCCOC)c(OCCOC)cc23)c1",
        "pubchem_cid": "176870",
        "chembl_id": "CHEMBL553",
        "context": "First-generation EGFR tyrosine kinase inhibitor reference for NSCLC treatment history.",
        "activity_evidence": "Reference EGFR inhibitor scaffold used for analog comparison.",
        "label_risk_context": [
            "Rash, diarrhea, anorexia, fatigue, dyspnea, cough, nausea, and vomiting are label-review topics.",
            "Interstitial lung disease or pneumonitis is a serious class-level label review topic.",
            "Hepatic, renal, ocular, and gastrointestinal perforation warnings may require label review.",
        ],
        "evidence_source": "Offline reference library; refresh PubChem, ChEMBL, and openFDA when live APIs are enabled.",
        "source_status": "fallback_reference",
    },
    {
        "drug_id": "afatinib",
        "name": "Afatinib",
        "smiles": "CN(C)C/C=C/C(=O)Nc1cc2c(Nc3ccc(F)c(Cl)c3)ncnc2cc1O[C@H]1CCOC1",
        "pubchem_cid": "10184653",
        "chembl_id": "CHEMBL1173655",
        "context": "Irreversible EGFR/HER-family tyrosine kinase inhibitor reference.",
        "activity_evidence": "Known irreversible EGFR-family inhibitor used as a structural and safety-context anchor.",
        "label_risk_context": [
            "Diarrhea, rash/acneiform dermatitis, stomatitis, paronychia, dry skin, and decreased appetite are review topics.",
            "Severe diarrhea, bullous/exfoliative skin disorders, and interstitial lung disease require label-level caution.",
            "Hepatic toxicity and keratitis are follow-up review topics.",
        ],
        "evidence_source": "Offline reference library; refresh PubChem, ChEMBL, and openFDA when live APIs are enabled.",
        "source_status": "fallback_reference",
    },
    {
        "drug_id": "osimertinib",
        "name": "Osimertinib",
        "smiles": "COc1cc(N(C)CCN(C)C)c(Nc2nccc(Nc3ccccc3)c2)c(OC)c1",
        "pubchem_cid": "71496458",
        "chembl_id": "CHEMBL3353410",
        "context": "Third-generation EGFR TKI reference, often discussed for EGFR sensitizing and T790M contexts.",
        "activity_evidence": "Known EGFR inhibitor reference used for analog and class-risk context.",
        "label_risk_context": [
            "Diarrhea, rash, dry skin, nail toxicity, and stomatitis are common review topics.",
            "Interstitial lung disease or pneumonitis requires label-level caution.",
            "QTc prolongation, cardiomyopathy, and ocular toxicity are important monitoring topics.",
        ],
        "evidence_source": "Offline reference library; refresh PubChem, ChEMBL, and openFDA when live APIs are enabled.",
        "source_status": "fallback_reference",
    },
    {
        "drug_id": "dacomitinib",
        "name": "Dacomitinib",
        "smiles": "COc1cc2ncnc(Nc3ccc(F)c(Cl)c3)c2cc1OCCCN1CCCCC1",
        "pubchem_cid": "11511120",
        "chembl_id": "CHEMBL2110732",
        "context": "Second-generation irreversible pan-HER/EGFR TKI reference.",
        "activity_evidence": "Known EGFR-family inhibitor reference for structural comparison.",
        "label_risk_context": [
            "Diarrhea, rash, paronychia, stomatitis, decreased appetite, dry skin, and weight decrease are review topics.",
            "Interstitial lung disease or pneumonitis is a serious label-level review topic.",
            "Hepatotoxicity and dermatologic toxicity may require dose-management review.",
        ],
        "evidence_source": "Offline reference library; refresh PubChem, ChEMBL, and openFDA when live APIs are enabled.",
        "source_status": "fallback_reference",
    },
    {
        "drug_id": "mobocertinib",
        "name": "Mobocertinib",
        "smiles": "COc1cc(N2CCN(CC2)C(=O)C=C)c(Nc2nccc(Nc3ccc(F)c(Cl)c3)n2)cc1N(C)CCN(C)C",
        "pubchem_cid": "9926791",
        "chembl_id": "CHEMBL4297518",
        "context": "EGFR exon 20 insertion inhibitor reference used for later-generation TKI risk context.",
        "activity_evidence": "Known EGFR inhibitor reference for structural and class-risk context.",
        "label_risk_context": [
            "Diarrhea, rash, nausea, stomatitis, vomiting, decreased appetite, and paronychia are review topics.",
            "QTc prolongation and cardiac toxicity are important label-level review topics.",
            "Interstitial lung disease or pneumonitis remains a serious class-level concern.",
        ],
        "evidence_source": "Offline reference library; refresh PubChem, ChEMBL, and openFDA when live APIs are enabled.",
        "source_status": "fallback_reference",
    },
]


def reference_drugs(include_structures: bool = True) -> list[dict[str, Any]]:
    drugs = deepcopy(REFERENCE_EGFR_DRUGS)
    if include_structures:
        for drug in drugs:
            drug["structure_svg"] = mol_svg_data_uri(str(drug["smiles"]))
    return drugs


def reference_drug(drug_id: str) -> dict[str, Any] | None:
    needle = drug_id.lower()
    for drug in reference_drugs(include_structures=True):
        if str(drug["drug_id"]).lower() == needle:
            return drug
    return None


def known_context_for_smiles(smiles: str, top_n: int = 4) -> dict[str, Any]:
    analogs: list[dict[str, Any]] = []
    for drug in reference_drugs(include_structures=False):
        similarity = tanimoto_like_similarity(smiles, str(drug["smiles"]))
        analogs.append(
            {
                "drug_id": drug["drug_id"],
                "name": drug["name"],
                "smiles": drug["smiles"],
                "pubchem_cid": drug["pubchem_cid"],
                "chembl_id": drug["chembl_id"],
                "similarity": round(similarity, 3),
                "label_risk_context": drug["label_risk_context"],
                "evidence_source": drug["evidence_source"],
                "source_status": drug["source_status"],
            }
        )
    analogs.sort(key=lambda item: float(item["similarity"]), reverse=True)
    return {
        "schema": "targetsafe.known_context.v1",
        "interpretation": (
            "Reference-drug adverse reactions are contextual review signals only; "
            "they are not candidate-specific toxicity conclusions."
        ),
        "nearest_known_drugs": analogs[:top_n],
    }


def fallback_drug_label_risks() -> list[dict[str, Any]]:
    risks: list[dict[str, Any]] = []
    for drug in REFERENCE_EGFR_DRUGS:
        risks.append(
            {
                "risk": f"{drug['name']} label review context",
                "drug_id": drug["drug_id"],
                "scope": "known/reference EGFR TKI label-level context",
                "interpretation": " ".join(drug["label_risk_context"]),
                "source_status": "fallback_reference",
            }
        )
    return risks
