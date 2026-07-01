from __future__ import annotations

import json
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from targetsafe.cache import SQLiteCache
from targetsafe.fallback_data import (
    FALLBACK_CHEMBL_ACTIVITIES,
    FALLBACK_TRIALS,
)
from targetsafe.models import EvidenceBundle, ToolCallLog
from targetsafe.observability import APIGate, RunLogger, classify_error
from targetsafe.reference_drugs import fallback_drug_label_risks, reference_drugs


class PublicDataSources:
    def __init__(self, cache: SQLiteCache, allow_network: bool = False, timeout: int = 8, logger: RunLogger | None = None) -> None:
        self.cache = cache
        self.allow_network = allow_network
        self.timeout = timeout
        self.logger = logger
        self.logs: list[ToolCallLog] = []
        self._circuit_failures: dict[str, int] = {}
        self._circuit_open_until: dict[str, float] = {}

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
                    message="Only EGFR has a validated target-specific activity fallback in this MVP.",
                    error_category="fallback",
                    provider="ChEMBL",
                    endpoint="target_profile_guard",
                    fallback_used=True,
                    severity="warning",
                )
            )
            return []

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
        cid_drugs = [drug for drug in drugs[:16] if str(drug.get("pubchem_cid") or "")]
        if cid_drugs:
            cid_list = ",".join(urllib.parse.quote(str(drug.get("pubchem_cid"))) for drug in cid_drugs)
            url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid_list}/property/CanonicalSMILES,IsomericSMILES,MolecularFormula,MolecularWeight/JSON"
            payload = self._fetch_json("PubChem", url, {"batch": "reference_cids"})
            props_by_cid = {
                str(item.get("CID") or ""): item
                for item in (payload or {}).get("PropertyTable", {}).get("Properties", [])
            }
            for drug in cid_drugs:
                cid = str(drug.get("pubchem_cid") or "")
                props = props_by_cid.get(cid)
                if props:
                    records.append(
                        {
                            "drug_id": drug.get("drug_id"),
                            "name": drug.get("name"),
                            "pubchem_cid": cid,
                            "canonical_smiles": props.get("CanonicalSMILES") or drug.get("smiles"),
                            "isomeric_smiles": props.get("IsomericSMILES"),
                            "molecular_formula": props.get("MolecularFormula"),
                            "molecular_weight": props.get("MolecularWeight"),
                            "source_status": "live_or_cached_batch",
                        }
                    )
                else:
                    records.append(
                        {
                            "drug_id": drug.get("drug_id"),
                            "name": drug.get("name"),
                            "pubchem_cid": cid,
                            "canonical_smiles": drug.get("smiles"),
                            "source_status": "fallback_reference",
                        }
                    )
        for drug in [item for item in drugs[:16] if not str(item.get("pubchem_cid") or "")]:
            cid = str(drug.get("pubchem_cid") or "")
            name = str(drug.get("name") or "")
            if cid:
                url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{urllib.parse.quote(cid)}/property/CanonicalSMILES,IsomericSMILES,MolecularFormula,MolecularWeight/JSON"
            elif name:
                url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{urllib.parse.quote(name)}/property/CanonicalSMILES,IsomericSMILES,MolecularFormula,MolecularWeight/JSON"
            else:
                continue
            payload = self._fetch_json("PubChem", url, {})
            if not payload:
                records.append(
                    {
                        "drug_id": drug.get("drug_id"),
                        "name": name,
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
                    "name": name,
                    "pubchem_cid": cid or str(props.get("CID") or ""),
                    "canonical_smiles": props.get("CanonicalSMILES") or drug.get("smiles"),
                    "isomeric_smiles": props.get("IsomericSMILES"),
                    "molecular_formula": props.get("MolecularFormula"),
                    "molecular_weight": props.get("MolecularWeight"),
                    "source_status": "live_or_cached",
                }
                )
        return records

    def circuit_summary(self) -> dict[str, Any]:
        now = time.time()
        return {
            "schema": "targetsafe.api_circuit_breaker.v1",
            "policy": "Per-run source circuit opens for 30 seconds after two repeated live-call failures.",
            "failures": dict(self._circuit_failures),
            "open_sources": {
                source: round(until - now, 2)
                for source, until in self._circuit_open_until.items()
                if until > now
            },
        }

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
        started = time.perf_counter()
        cache_query = {"url": url, "params": params}
        gate = APIGate(
            provider=source,
            enabled=self.allow_network,
            requires_key=False,
            timeout_seconds=self.timeout,
            cache_fallback=True,
            logger=self.logger,
        )
        gate_payload = gate.check(endpoint=url, source=source)
        cached = self.cache.get(source, cache_query, ttl_seconds=86400)
        if cached is not None:
            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            if self.logger:
                self.logger.log(
                    "tool_call_finished",
                    source=source,
                    status="cached",
                    endpoint=url,
                    duration_ms=duration_ms,
                    fallback_used=False,
                )
            self.logs.append(
                ToolCallLog(
                    source=source,
                    query=json.dumps(cache_query),
                    status="ok",
                    cached=True,
                    item_count=1,
                    error_category="cached",
                    duration_ms=duration_ms,
                    provider=source,
                    endpoint=url,
                    fallback_used=False,
                    debug_ref=self.logger.path.name if self.logger else "",
                )
            )
            return cached
        negative = self.cache.get_negative(source, cache_query, ttl_seconds=180)
        if negative:
            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            category = str(negative.get("error_category") or negative.get("error_code") or "cached_negative")
            self.logs.append(
                ToolCallLog(
                    source=source,
                    query=json.dumps(cache_query),
                    status="fallback",
                    cached=True,
                    item_count=0,
                    message=f"Recent negative cache hit: {category}.",
                    error_category=category,
                    duration_ms=duration_ms,
                    provider=source,
                    endpoint=url,
                    error_code=category,
                    severity="info",
                    fallback_used=True,
                    debug_ref=self.logger.path.name if self.logger else "",
                )
            )
            return None
        if self._is_circuit_open(source):
            stale = self.cache.get_stale(source, cache_query)
            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            if self.logger:
                self.logger.log("fallback_selected", source=source, reason="circuit_open", endpoint=url, duration_ms=duration_ms)
            self.logs.append(
                ToolCallLog(
                    source=source,
                    query=json.dumps(cache_query),
                    status="fallback",
                    cached=stale is not None,
                    item_count=1 if stale is not None else 0,
                    message="API circuit is temporarily open after repeated failures; using stale cache if available.",
                    error_category="circuit_open",
                    duration_ms=duration_ms,
                    provider=source,
                    endpoint=url,
                    error_code="circuit_open",
                    severity="warning",
                    fallback_used=True,
                    debug_ref=self.logger.path.name if self.logger else "",
                )
            )
            return stale
        if not gate_payload["allowed"]:
            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            error = classify_error(
                str(gate_payload.get("reason") or "network_disabled"),
                source,
                "Network/API gate denied live request.",
                run_id=self.logger.run_id if self.logger else "",
                fallback_used=True,
            )
            if self.logger:
                self.logger.log_error(error)
                self.logger.log(
                    "fallback_selected",
                    source=source,
                    reason=error.error_code,
                    endpoint=url,
                    duration_ms=duration_ms,
                )
            self.logs.append(
                ToolCallLog(
                    source=source,
                    query=json.dumps(cache_query),
                    status="fallback",
                    cached=False,
                    message="Network disabled; using fallback evidence.",
                    error_category=str(gate_payload.get("reason") or "network_disabled"),
                    duration_ms=duration_ms,
                    provider=source,
                    endpoint=url,
                    error_code=str(gate_payload.get("reason") or "network_disabled"),
                    severity="warning",
                    fallback_used=True,
                    debug_ref=self.logger.path.name if self.logger else "",
                )
            )
            return None
        full_url = f"{url}?{urllib.parse.urlencode(params)}"
        request = urllib.request.Request(full_url, headers={"Accept": "application/json", "User-Agent": "TargetSAFE/0.1"})
        try:
            if self.logger:
                self.logger.log("tool_call_started", source=source, endpoint=url, query=full_url)
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
            self.cache.set(source, cache_query, payload)
            item_count = len(payload.get("activities", payload.get("studies", payload.get("results", []))))
            status = "ok" if item_count else "empty"
            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            if self.logger:
                self.logger.log(
                    "tool_call_finished",
                    source=source,
                    status=status,
                    endpoint=url,
                    item_count=item_count,
                    duration_ms=duration_ms,
                    fallback_used=status != "ok",
                )
            if status == "ok":
                self._record_circuit_success(source)
            else:
                self._record_circuit_failure(source)
                self.cache.set(
                    source,
                    cache_query,
                    {"error_category": "http_empty", "created_at": time.time()},
                    ttl_seconds=180,
                    negative=True,
                )
            self.logs.append(
                ToolCallLog(
                    source=source,
                    query=full_url,
                    status=status,
                    cached=False,
                    item_count=item_count,
                    error_category="" if item_count else "http_empty",
                    message="" if item_count else "Live API returned no rows; fallback evidence may be used.",
                    duration_ms=duration_ms,
                    provider=source,
                    endpoint=url,
                    error_code="" if item_count else "http_empty",
                    severity="info" if item_count else "warning",
                    fallback_used=not bool(item_count),
                    debug_ref=self.logger.path.name if self.logger else "",
                )
            )
            return payload
        except Exception as exc:
            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            category = _categorize_fetch_error(exc)
            error = classify_error(
                category,
                source,
                str(exc),
                run_id=self.logger.run_id if self.logger else "",
                fallback_used=True,
            )
            if self.logger:
                self.logger.log("tool_call_failed", source=source, endpoint=url, query=full_url, duration_ms=duration_ms, error=error.to_dict())
                self.logger.log_error(error)
                self.logger.log("fallback_selected", source=source, reason=category, endpoint=url)
            self._record_circuit_failure(source)
            stale = self.cache.get_stale(source, cache_query)
            self.cache.set(
                source,
                cache_query,
                {"error_category": category, "message": str(exc), "created_at": time.time()},
                ttl_seconds=180,
                negative=True,
            )
            self.logs.append(
                ToolCallLog(
                    source=source,
                    query=full_url,
                    status="error",
                    cached=stale is not None,
                    message=str(exc),
                    error_category=category,
                    duration_ms=duration_ms,
                    provider=source,
                    endpoint=url,
                    error_code=category,
                    severity="warning",
                    fallback_used=True,
                    debug_ref=self.logger.path.name if self.logger else "",
                )
            )
            return stale

    def _is_circuit_open(self, source: str) -> bool:
        return self._circuit_open_until.get(source, 0.0) > time.time()

    def _record_circuit_success(self, source: str) -> None:
        self._circuit_failures[source] = 0
        self._circuit_open_until.pop(source, None)

    def _record_circuit_failure(self, source: str) -> None:
        failures = self._circuit_failures.get(source, 0) + 1
        self._circuit_failures[source] = failures
        if failures >= 2:
            self._circuit_open_until[source] = time.time() + 30


def _categorize_fetch_error(exc: Exception) -> str:
    if isinstance(exc, urllib.error.HTTPError):
        if exc.code == 404:
            return "http_empty"
        if exc.code == 429:
            return "rate_limited"
        return f"http_{exc.code}"
    if isinstance(exc, (TimeoutError, socket.timeout)):
        return "timeout"
    text = str(exc).lower()
    if "10061" in text or "connection refused" in text or "actively refused" in text:
        return "network_refused"
    if "timed out" in text or "timeout" in text:
        return "timeout"
    if isinstance(exc, json.JSONDecodeError):
        return "parse_error"
    return "unknown_error"
