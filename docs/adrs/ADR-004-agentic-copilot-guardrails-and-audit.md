# ADR-004: Agentic AI Guardrails & Regulatory Compliance Audit Trail

## Status
Accepted

## Context
Section 7, 8 & 11 mandate an Agentic AI layer with:
- "An agent that answers or acts on fleet data, with guardrails and an audit trail"
- "Compliance with UNECE R155/R156, India DPDP Act 2023, and GDPR right-to-erasure / data masking"
- Prompt-injection defense and bounded tool permissions

Giving an autonomous LLM unconstrained write access to vehicle fleets creates catastrophic physical and cyber safety hazards.

## Options Considered
1. **Unbounded LLM ReAct Loop with Raw SQL Execution**: Extreme risk of SQL injection, hallucinated queries, or accidental drop commands.
2. **Read-Only Dashboard Summary**: Completely misses the prompt's Agentic AI requirement ("moving from dashboards to recommending and taking actions").
3. **Structured Guarded Tool Invocation with Deterministic Policy & Audit Trail (Selected)**:
   - The LLM agent interacts exclusively via bounded, typed Python tools:
     - `get_vehicle_diagnostics(vin)`
     - `calculate_repair_roi(vin)`
     - `search_oem_knowledge(dtc_code)`
   - Every single tool invocation, parameter set, actor identity, and IP address is committed to the relational `audit_logs` table.
   - Input strings are scrubbed for prompt injection vectors (`"ignore previous instructions"`, `"drop table"`).

## Decision
Implement `FleetCopilotAgent` with structured tool calling and automatic audit logging.

## Consequences
- **Positive**: Strict regulatory compliance (audit logs available for automotive homologation audits under UNECE R155); 0% chance of unauthorized arbitrary code execution.
- **Negative**: Dynamic ad-hoc queries outside the predefined tool signatures must be handled through predefined analytical routes.
