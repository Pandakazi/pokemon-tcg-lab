# ADR 002 — Conversation First, Evidence Underneath

Date: 2026-10-03. Status: implemented for PM QA, not certified.

ADR 001 lives at `docs/adr-001-web-first.md`; this is the next number.

## Context

Phase 7C.3 intentionally pursued strong evidence grounding and strict answer validation. PM testing showed that validating arbitrary natural-language prose against structured evidence caused false rejection, brittle UX and wasted inference. Raw model experiments showed stronger conversational reasoning but factual drift; those experiments are behavioral references, never truth fixtures.

## Locked principles

1. CONVERSATION FIRST. EVIDENCE UNDERNEATH.
2. POKÉLAB-FIRST, NOT POKÉLAB-ONLY.
3. POKÉLAB SUPPLIES TRUTH. THE MODEL SUPPLIES INTELLIGENCE.
4. VERIFICATION SHOULD CORRECT MODEL INPUTS AND HIGH-VALUE FACTUAL / EMPIRICAL CLAIMS, NOT MICROMANAGE ORDINARY CONVERSATIONAL PROSE.
5. EVIDENCE IS INSPECTABLE, NOT INTRUSIVE.
6. THE AGENT PROPOSES. THE PLAYER DECIDES. POKÉLAB REMEMBERS.

The sixth principle remains a broader product direction. This phase remembers only recent conversation in process/browser memory; it does not implement durable memory or write actions.

## Decision

The default Agent uses `conversational_default`. Existing explicit research scopes retain `strict_research` behavior internally, their existing contracts, validators, evidence packets, provenance, fact projections and fixtures. No user mode selector is added.

A bounded deterministic orchestrator supplies current local facts and previous conversational referents to one explicitly configured provider. Standard card-pool retrieval is a resource, not a prerequisite for answering. A small intent alias layer translates common natural requests into existing search concepts without modifying Pass 2 retrieval, scores, taxonomy or caps. Empty results and lack of empirical evidence do not prohibit general reasoning.

Exact selected-card data, names/components found locally, complete active-deck contents and revision, ownership, and available selected-card competitive/rules evidence enter the prompt as source-owned values. Source-selected `fact_ids` render those values directly; models cannot supply replacement factual payloads. The model may reason, synthesize, teach, coach, compare and brainstorm without running ordinary paragraphs through the strict research prose validators.

Schema, citation membership, source ownership, input/output bounds, source snapshots, secret quarantine, completion, single-flight execution and the zero-cost policy remain strict. High-value empirical prose is restricted to source-rendered facts; a deliberately bounded detector withholds paragraphs containing recognizable percentages, win-rate/tier/most-played/event-dominance assertions and adds a neutral qualification. It does not judge every strategic sentence. This is not universal semantic verification; exact-fact injection constrains reasoning but cannot prove every model paraphrase. PM must evaluate live factual fidelity and usefulness.

## Consequences

Evidence remains inspectable underneath the answer, including Fact / Evidence / Inference distinctions on proof requests. Existing card previews and evidence rendering are reused. Available, unambiguous attack/Ability names reuse the same popover for exact printed effect text.

Recent accepted turns and candidate printings live in a bounded, expiring server cache; the browser keeps an opaque conversation ID. Fresh local retrieval supersedes old factual context. Prior answers/proposals are explicitly not authority, actual saved decks, instructions or creator intent. Compacted history is labeled in provider context. Reload/server restart/expiry can lose continuity. No credentials, rejected output or hidden reasoning is stored.

No reusable general external strategy/web-research service exists in the current product path. Existing card/tournament ingestion is not repurposed as browsing. `external_research=false` is a capability boundary; the Agent must not claim external research.

The preserved strict infrastructure remains useful for exact printed facts, Standard legality, tournament statistics, empirical claims, provenance and proof on demand. A scientific/research-heavy experience may later expose claim-level sourcing, explicit provenance, confidence and methodology if users demonstrate demand. This phase introduces neither that mode nor a policy engine, routing, benchmark expansion, persistent profiles, deck actions or Phase 7D.
