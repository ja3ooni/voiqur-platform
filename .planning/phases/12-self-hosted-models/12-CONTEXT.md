# Phase 12 Context: Self-Hosted Models

## Phase
12 - Self-Hosted Models

## Goal
vLLM deployment, OpenAI-compatible API, Voxtral STT fallback, model fallback chain

## Requirements
- SELF-01: vLLM server deployment for Mistral inference
- SELF-02: Self-hosted LLM API endpoint with OpenAI-compatible interface
- SELF-03: Voxtral STT integration (when released by Mistral)
- SELF-04: Model fallback chain: API → self-hosted

## Discussion Summary

### vLLM Deployment
1. vLLM server with Mistral model
2. OpenAI-compatible /v1/completions and /v1/chat/completions endpoints
3. Streaming support
4. GPU memory management

### Fallback Chain
1. Primary: Mistral API (existing)
2. Failover: Self-hosted vLLM
3. Error handling and circuit breaker

### Voxtral STT
- Wait for Mistral release
- Integration point when available

---
*Discussed: 2026-04-25*