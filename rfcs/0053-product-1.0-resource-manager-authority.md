# RFC 0053 — Product 1.0 Resource Manager Authority

## Status

Draft

## Summary

This RFC defines the authoritative boundary for Resource Manager in Product 1.0.

## Decision required

- standalone service
- embedded kernel module
- hybrid boundary with stable internal API

## Normative consequences

- inventory ownership
- reservation ownership
- queue pressure visibility
- fairness / quota policy source
- replay-safe resource lineage

## Required follow-up

- ADR for deployment model
- inventory contract update
- compatibility report update
