from __future__ import annotations

import json
import urllib.parse
import urllib.request
from typing import Any

from targetsafe.cache import SQLiteCache
from targetsafe.fallback_data import (
    FALLBACK_CHEMBL_ACTIVITIES,
    FALLBACK_TRIALS,
)
from targetsafe.models import EvidenceBundle, ToolCallLog
from targetsafe.reference_drugs import fallback_drug_label_risks, reference_drugs


class PublicDataSources:
    def __init__(self, cache: SQLiteCache, allow_network: bool = False, timeout: int = 8) -> None:
        self.cache = cache
        self.allow_network = allow_network
        self.timeout = timeout
        self.logs: list[ToolCallLog] = []

    def collect_evidence(self, disease: str, target: str) -> EvidenceBundle:
        known_drugs = reference_drugs(include_structures=False)
        activities = self.get_chembl_egfr_activities(target)
        pubchem_records = self.get_pubchem_reference_records(known_drugs)
        trials = self.get_clinical_trials(disease, target)
        regulatory = self.get_openfda_label_risks(target, known_drugs)
        notes = [
            "Candidate-level clinical claims are not made; clinical/regulatory evidence is class-level context.",
            "Offline fallback data is marked as demo context when public APIs are disabled or unavailable.",
            "Known-drug adverse reactions are reference/label context, not candidate-specific toxicity predictions.",
        ]
        return EvidenceBundle(
            target=target,
            disease=disease,
            chembl_activities=activities,
            pubchem_records=pubchem_records,
            clinical_trials=trials,
            regulatory_risks=regulatory,
            known_inhibitors=known_drugs,
            evidence_notes=notes,
        )

    def get_chembl_egfr_activities(self, target: str) -> list[dict[str, Any]]:
        if target.upper() != "EGFR":
            self.logs.append(
                ToolCallLog(
                    source="ChEMBL",
                    query=f"target={target}",
                    status="fallback",
                    item_count=len(FALLBACK_CHEMBL_ACTIVITIES),
                    message="Only EGFR is implemented for the MVP.",
                )
            )
            return FALLBACK_CHEMBL_ACTIVITIES

        url = "https://www.ebi.ac.uk/chembl/api/data/activity.json"
        params = {
            "target_chembl_id": "CHEMBL203",
            "standard_type": "IC50",
            "standard_units": "nM",
            "limit": 100,
        }
        payload = self._fetch_json("ChEMBL", url, params)
        if not payload:
            return FALLBACK_CHEMBL_ACTIVITIES
        activities = payload.get("activities") or []
        if not activities:
            return FALLBACK_CHEMBL_ACTIVITIES
        return activities[:100]

    def get_clinical_trials(self, disease: str, target: str) -> list[dict[str, Any]]:
        url = "https://clinicaltrials.gov/api/v2/studies"
        params = {"query.cond": disease, "query.term": target, "format": "json", "pageSize": 10}
        payload = self._fetch_json("ClinicalTrials.gov", url, params)
        if not payload:
            return FALLBACK_TRIALS
        trials: list[dict[str, Any]] = []
        for study in payload.get("studies", [])[:10]:
            protocol = study.get("protocolSection", {})
            ident = protocol.get("identificationModule", {})
            status = protocol.get("statusModule", {})
            design = protocol.get("designModule", {})
            phases = design.get("phases") or []
            trials.append(
                {
                    "nctId": ident.get("nctId", ""),
                    "briefTitle": ident.get("briefTitle", ""),
                    "overallStatus": status.get("overallStatus", ""),
                    "phase": ", ".join(phases) if isinstance(phases, list) else str(phases),
                }
            )
        return trials or FALLBACK_TRIALS

    def get_pubchem_reference_records(self, drugs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for drug in drugs[:8]:
            cid = str(drug.get("pubchem_cid") or "")
            if not cid:
                continue
            url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{urllib.parse.quote(cid)}/property/CanonicalSMILES,IsomericSMILES,MolecularFormula,MolecularWeight/JSON"
            payload = self._fetch_json("PubChem", url, {})
            if not payload:
                records.append(
                    {
                        "drug_id": drug.get("drug_id"),
                        "name": drug.get("name"),
                        "pubchem_cid": cid,
                        "canonical_smiles": drug.get("smiles"),
                        "source_status": "fallback_reference",
                    }
                )
                continue
            props = (payload.get("PropertyTable", {}).get("Properties") or [{}])[0]
            records.append(
                {
                    "drug_id": drug.get("drug_id"),
                    "name": drug.get("name"),
                    "pubchem_cid": cid,
                    "canonical_smiles": props.get("CanonicalSMILES") or drug.get("smiles"),
                    "isomeric_smiles": props.get("IsomericSMILES"),
                    "molecular_formula": props.get("MolecularFormula"),
                    "molecular_weight": props.get("MolecularWeight"),
                    "source_status": "live_or_cached",
                }
            )
        return records

    def get_openfda_label_risks(self, target: str, drugs: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
        risks: list[dict[str, Any]] = []
        for drug in (drugs or [])[:8]:
            query = f'openfda.generic_name:"{drug.get("name")}" OR openfda.brand_name:"{drug.get("name")}"'
            url = "https://api.fda.gov/drug/label.json"
            params = {"search": query, "limit": 1}
            payload = self._fetch_json("openFDA label", url, params)
            if not payload:
                continue
            for result in payload.get("results", [])[:1]:
                warnings = result.get("warnings_and_cautions") or result.get("warnings") or []
                adverse = result.get("adverse_reactions") or []
                risks.append(
                    {
                        "risk": f"{drug.get('name')} label review context",
                        "drug_id": drug.get("drug_id"),
                        "scope": "drug-specific openFDA label signal",
                        "interpretation": " ".join((warnings[:1] + adverse[:1]))[:900]
                        or "Review label warnings and adverse reactions.",
                        "source_status": "live_or_cached",
                    }
                )
        if risks:
            return risks

        query = 'openfda.pharm_class_epc:"Epidermal growth factor receptor inhibitor"'
        url = "https://api.fda.gov/drug/label.json"
        params = {"search": query, "limit": 5}
        payload = self._fetch_json("openFDA label", url, params)
        if not payload:
            return fallback_drug_label_risks()

        for result in payload.get("results", [])[:5]:
            name = ", ".join(result.get("openfda", {}).get("brand_name", [])[:2])
            warnings = result.get("warnings_and_cautions") or result.get("warnings") or []
            adverse = result.get("adverse_reactions") or []
            text = " ".join(warnings[:1] + adverse[:1])
            risks.append(
                {
                    "risk": name or f"{target} inhibitor label signal",
                    "scope": "openFDA drug label class-level signal",
                    "interpretation": text[:500] if text else "Review label warnings and adverse reactions.",
                    "source_status": "live_or_cached",
                }
            )
        return risks or fallback_drug_label_risks()

    def _fetch_json(self, source: str, url: str, params: dict[str, Any]) -> dict[str, Any] | None:
        cache_query = {"url": url, "params": params}
        cached = self.cache.get(source, cache_query, ttl_seconds=86400)
        if cached is not None:
            self.logs.append(
                ToolCallLog(source=source, query=json.dumps(cache_query), status="ok", cached=True, item_count=1)
            )
            return cached
        if not self.allow_network:
            self.logs.append(
                ToolCallLog(
                    source=source,
                    query=json.dumps(cache_query),
                    status="fallback",
                    cached=False,
                    message="Network disabled; using fallback evidence.",
                )
            )
            return None
        full_url = f"{url}?{urllib.parse.urlencode(params)}"
        request = urllib.request.Request(full_url, headers={"Accept": "application/json", "User-Agent": "TargetSAFE/0.1"})
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
            self.cache.set(source, cache_query, payload)
            item_count = len(payload.get("activities", payload.get("studies", payload.get("results", []))))
            self.logs.append(
                ToolCallLog(source=source, query=full_url, status="ok", cached=False, item_count=item_count)
            )
            return payload
        except Exception as exc:
            self.logs.append(
                ToolCallLog(source=source, query=full_url, status="error", cached=False, message=str(exc))
            )
            return None
