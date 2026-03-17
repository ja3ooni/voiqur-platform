# Voiquyr Task Plan

This document outlines the tasks required to build the Voiquyr platform, based on the Product Requirements Document (PRD).

## Phase 1: MVP

The focus of the MVP is to build the core orchestrator, implement SIP trunking, and deploy the system to the EU region (Frankfurt).

### 1. Project Setup & Scaffolding

*   [ ] Set up a monorepo to manage the frontend and backend code.
*   [ ] Create a CI/CD pipeline for automated testing and deployment.

### 2. Core Orchestrator (Backend)

*   [ ] Implement a basic FastAPI application.
*   [ ] Define the core data models (User, Call, SIPTrunk, etc.).
*   [ ] Implement user authentication and API key management.
*   [ ] Set up a database (PostgreSQL or MongoDB).

### 3. SIP Trunking (Backend)

*   [ ] Integrate a SIP library (e.g., `aiortc` for Python).
*   [ ] Implement a generic SIP adapter to accept credentials.
*   [ ] Implement RTP stream handling.

### 4. EU Region (Frankfurt) Deployment

*   [ ] Create a Dockerfile for the backend.
*   [ ] Write a docker-compose file for local development.
*   [ ] Create a deployment script for deploying to a cloud provider (e.g., AWS, GCP, Azure) in the Frankfurt region.

### 5. Dashboard (Frontend)

*   [ ] Create a new page for SIP trunk configuration.
*   [ ] Create a new page for viewing call logs.
*   [ ] Create a new page for viewing billing information.

### 6. Documentation

*   [ ] Create API documentation for the backend.
*   [ ] Create user documentation for the dashboard.

## Phase 2: Expansion

*   [ ] Deploy to Middle East Region (Bahrain).
*   [ ] Implement Arabic Dialect Support.

## Phase 3: Scale

*   [ ] Deploy to Asia Region (Mumbai/Singapore).
*   [ ] Implement "Flash Mode" Speculative Inference.
