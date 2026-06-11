# RFC / ADR Gap Closure Matrix

Wave 5 is the governance closure wave for Product 1.0. The goal of this wave is not to add new runtime capabilities, but to ensure that every required contract, operational requirement, decision record, and lifecycle policy has a canonical source of truth and traceability to a release artifact.

## Closure Matrix

| Gap ID | Gap Description | Required Document | Primary Owner | Reviewers | Closure Artifact |
|---------|----------------|------------------|--------------|-----------|------------------|
| W5-GOV-001 | No single ownership map for Product 1.0 contracts | product-1.0-governance-model.md | Architecture | Platform | Governance approval record |
| W5-GOV-002 | Contract lifecycle after GA is undefined | product-1.0-contract-lifecycle-policy.md | Architecture | Product | Lifecycle policy ratification |
| W5-GOV-003 | Deprecation/removal process is undefined | product-1.0-deprecation-policy.md | Architecture | Product | Deprecation policy approval |
| W5-GOV-004 | Schema exception handling process is missing | product-1.0-schema-exception-process.md | API Governance | Architecture | Exception register |
| W5-GOV-005 | Formal compatibility authority is missing | product-1.0-compatibility-governance.md | Architecture | Platform | Compatibility certification workflow |
| W5-GOV-006 | Protobuf evolution ownership is undefined | adr-product-1.0-protobuf-evolution.md | API Governance | Runtime | ADR acceptance |
| W5-GOV-007 | Envelope versioning authority decision is missing | adr-product-1.0-envelope-governance.md | Architecture | Runtime | ADR acceptance |
| W5-GOV-008 | Observability contract governance model is missing | adr-product-1.0-observability-governance.md | SRE | Architecture | ADR acceptance |
| W5-GOV-009 | Public error catalog authority is undefined | adr-product-1.0-error-governance.md | API Governance | Product | ADR acceptance |
| W5-GOV-010 | Replay determinism guarantees lack governance authority | adr-product-1.0-determinism-authority.md | Runtime | Architecture | ADR acceptance |
| W5-GOV-011 | Contract audit program is missing | product-1.0-contract-audit-program.md | Compliance | Architecture | Annual audit report template |
| W5-GOV-012 | Reference documentation governance is missing | product-1.0-documentation-governance.md | Documentation | Architecture | Documentation ownership registry |
| W5-GOV-013 | Formal release-signoff checklist is missing | product-1.0-release-signoff.md | Release Engineering | Product | Signed release checklist |
| W5-GOV-014 | Contract waiver process is missing | product-1.0-contract-waiver-process.md | Architecture | Compliance | Waiver register |
| W5-GOV-015 | Exception escalation path is missing | product-1.0-escalation-model.md | Architecture | Product | Escalation matrix |
| W5-GOV-016 | Change control board definition is missing | product-1.0-change-control-board.md | Product | Architecture | CCB charter |
| W5-GOV-017 | Authoritative RFC inventory baseline is missing | product-1.0-rfc-registry.md | Architecture | Documentation | RFC registry |
| W5-GOV-018 | Authoritative ADR registry is missing | product-1.0-adr-registry.md | Architecture | Documentation | ADR registry |
| W5-GOV-019 | Mandatory review gates are undefined | product-1.0-review-gates.md | Product | Architecture | Review gate checklist |
| W5-GOV-020 | Governance document lifecycle model is missing | product-1.0-governance-lifecycle.md | Architecture | Documentation | Governance lifecycle approval |

## RFC Coverage Gaps

| RFC Area | Existing Coverage | Gap | Closure Document |
|-----------|------------------|-----|------------------|
| Public API Contracts | Partial | Governance authority undefined | product-1.0-compatibility-governance.md |
| Error Taxonomy | Partial | Ownership undefined | adr-product-1.0-error-governance.md |
| Envelope Versioning | Technical only | Governance missing | adr-product-1.0-envelope-governance.md |
| Determinism Guarantees | Runtime implementation exists | Authority missing | adr-product-1.0-determinism-authority.md |
| Observability Contracts | Runtime implementation exists | Stewardship undefined | adr-product-1.0-observability-governance.md |
| Schema Evolution | Version policy exists | Exception process missing | product-1.0-schema-exception-process.md |
| Contract Lifecycle | Inventory exists | Lifecycle governance missing | product-1.0-contract-lifecycle-policy.md |
| Deprecation | Version policy partially covers | Removal governance absent | product-1.0-deprecation-policy.md |

## ADR Coverage Gaps

| ADR Domain | Existing ADRs | Missing Decision | New ADR |
|------------|---------------|------------------|---------|
| Public Compatibility | Partial | Who approves breaking changes | adr-product-1.0-compatibility-authority.md |
| Protobuf Evolution | Technical rules scattered | Governance decision absent | adr-product-1.0-protobuf-evolution.md |
| Envelope Governance | Runtime-focused | Ownership undefined | adr-product-1.0-envelope-governance.md |
| Error Catalog | Runtime-focused | Stewardship undefined | adr-product-1.0-error-governance.md |
| Determinism | Runtime-focused | Certification authority undefined | adr-product-1.0-determinism-authority.md |
| Observability | Runtime-focused | Ownership undefined | adr-product-1.0-observability-governance.md |

## Required Closure Evidence

Each gap is considered closed only after the following artifacts exist:

| Evidence Type | Required |
|--------------|----------|
| Governance document merged | Yes |
| Architecture review completed | Yes |
| Ownership assigned | Yes |
| Registry updated | Yes |
| Product 1.0 inventory cross-linked | Yes |
| Contract alignment plan updated | Yes |
| Release signoff references document | Yes |

## Exit Criteria

Wave 5 is complete only if:

- All Gap IDs are marked CLOSED.
- All new RFCs and ADRs are registered in the appropriate registry.
- All governance documents are linked from the Product 1.0 inventory.
- All Product 1.0 contracts have an owner.
- All exception paths are documented.
- All deprecation paths are documented.
- Release signoff uses governance artifacts as mandatory inputs.
- No RFC or ADR exists without ownership and lifecycle metadata.
