Product Requirements Document (PRD): Voiquyr

Version: 1.0
Status: Approved for Development
Focus: EU, Middle East, & Asia (India, SE Asia) Localization & Sovereignty

1. Executive Summary

Voiquyr is a Commercial Shared-Source Voice AI Platform designed to replace Vapi in non-US markets. Unlike US-centric competitors, Voiquyr prioritizes Data Sovereignty (Region-Locked Routing), Telephony Independence (Bring Your Own Carrier), and Hyper-Localization (Code-switching & Dialects).

The system targets a <500ms conversational latency benchmark across Europe, the Middle East, and Asia by leveraging edge computing and speculative inference.

2. System Architecture & Latency Requirements

Requirement 2.1: Regional Edge Orchestration (The "Anti-Lag" Layer)

User Story: As a user in Dubai, I want my call routed through a local server so there is no audio delay.

2.1.1 Region-Locked Routing: The system SHALL route audio streams (RTP) exclusively within the client's designated sovereignty zone (e.g., a call in UAE utilizes the Bahrain/UAE AWS region; data MUST NOT exit to Europe or US).

2.1.2 Distributed Topology: The Orchestrator MUST be deployable as a stateless microservice on edge nodes (Frankfurt, Mumbai, Bahrain, Singapore, Tokyo).

2.1.3 Protocol Optimization: The audio pipeline SHALL use WebSockets or gRPC for internal streaming, bypassing HTTP overhead.

Requirement 2.2: "Flash Mode" Speculative Inference

User Story: As a user, I want the AI to start answering before I have even fully finished my sentence, just like a human.

2.2.1 Prediction: When STT confidence exceeds 85%, the LLM SHALL begin speculative inference on the user's intent before the final end-of-turn token is received.

2.2.2 Time-to-First-Byte (TTFB): The TTS engine MUST begin streaming audio bytes <200ms after the first LLM token is generated.

Requirement 2.3: Intelligent Voice Activity Detection (VAD)

User Story: As a user, I do not want the AI to interrupt me when I am just pausing to think.

2.3.1 Semantic End-of-Turn: The VAD model SHALL analyze not just silence duration, but also prosody (pitch/tone) and semantic completeness to distinguish a "thinking pause" from a "finished sentence."

2.3.2 Barge-In Handling: If the user speaks while the AI is talking, the system MUST:

Immediately stop audio playback (<50ms).

Clear the current audio buffer.

Retain the context of what was not said for the next turn.

3. Telephony & Integration (The "BYOC" Moat)

Requirement 3.1: SIP Trunking & Bring Your Own Carrier (BYOC)

User Story: As a BPO in India, I want to use my existing, low-cost Tata/Jio SIP trunks instead of buying expensive numbers from you.

3.1.1 Generic SIP Adapter: The platform SHALL accept standard SIP credentials (URI, User, Pass) from any major carrier (Twilio, Tata, Vonage, generic PBX).

3.1.2 Direct RTP Streaming: The system SHALL support direct media handling where the audio stream flows directly from the carrier to the Voiquyr Edge Node, minimizing hops.

3.1.3 Legacy Integration: The system SHALL support transfer-to-PSTN (warm handoff) to connect legacy contact center agents (Avaya/Genesys) when AI fails.

4. Localization & Linguistic Intelligence

Requirement 4.1: Low-Resource Language Optimization

User Story: As an Estonian bank, I need an AI that speaks flawless Estonian, not just "translated English."

4.1.1 Open-Weights Fine-Tuning: The system SHALL utilize state-of-the-art open-weights models (e.g., Llama 3, Mistral, Gemma equivalents) fine-tuned via LoRA adapters for: Croatian, Estonian, Maltese, Czech, and Polish.

4.1.2 EuroHPC Utilization: Training pipelines SHALL leverage EU-based GPU infrastructure (EuroHPC) where possible to ensure data sovereignty during the training phase.

Requirement 4.2: Arabic & "Code-Switching" Excellence

User Story: As a customer in Cairo, I speak a mix of Egyptian Arabic and English ("Hinglish" equivalent). The AI must understand this mix.

4.2.1 Dialect Recognition: The STT engine MUST distinguish between MSA (Modern Standard Arabic), Egyptian, Levantine, Gulf, and Maghrebi dialects.

4.2.2 Code-Switching: The LLM MUST be fine-tuned to handle mid-sentence language swaps (e.g., Arabic to English, Hindi to English) without breaking context.

4.2.3 Cultural Diacritization: TTS output for Arabic MUST apply correct diacritics based on the detected regional dialect to ensure natural pronunciation.

5. Business & Operational Requirements

Requirement 5.1: Unified & Localized Billing

User Story: As a business in Singapore, I want one invoice in SGD, not five invoices from different API providers.

5.1.1 Unified Cost Per Minute (UCPM): The billing engine SHALL bundle STT, LLM, TTS, and Orchestration into a single per-minute rate.

5.1.2 Local Currency Support: The platform MUST invoice natively in EUR, AED, INR, SGD, and JPY to avoid forex friction for clients.

Requirement 5.2: Compliance & Data Sovereignty

User Story: As a German healthcare provider, I am legally forbidden from sending patient voice data to the US.

5.2.1 Region Locking: The dashboard MUST allow Admins to select a "Home Region." Once selected, no data (logs, audio, transcripts) may be replicated outside that region.

5.2.2 PII Redaction: The system SHALL optionally redact Personally Identifiable Information (PII) from logs before storage.

Requirement 5.3: Security & Fraud Prevention

User Story: As the platform owner, I need to prevent users from draining my GPU credits via bot attacks.

5.3.1 Rate Limiting: The system SHALL implement concurrent call limits per API key.

5.3.2 Abnormal Pattern Detection: The system SHALL flag and auto-terminate calls exceeding a set duration (e.g., >45 mins) or repeating loops, to prevent resource draining.

6. Roadmap & Implementation Priorities

Phase 1 (The MVP): Core Orchestrator + SIP Trunking + EU Region (Frankfurt).

Phase 2 (Expansion): Middle East Region (Bahrain) + Arabic Dialect Support.

Phase 3 (Scale): Asia Region (Mumbai/Singapore) + "Flash Mode" Speculative Inference.
