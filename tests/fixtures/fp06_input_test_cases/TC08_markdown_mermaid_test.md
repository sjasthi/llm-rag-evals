
# Metro State Graduate Application Review Process

## Overview

This document describes a fictional graduate application review process used for testing the RAG EVAL 2.0 system.

Applicants must submit an application, official transcripts, and a statement of purpose.

## Application Review Workflow

The following Mermaid diagram illustrates the application review process.

```mermaid
flowchart TD
    A[Student Submits Application] --> B{All Documents Received?}
    B -->|No| C[Request Missing Documents]
    C --> D[Wait for Student Response]
    D --> B
    B -->|Yes| E{Minimum GPA 3.0 Met?}
    E -->|No| F[Application Rejected]
    E -->|Yes| G[Faculty Committee Review]
    G --> H{Committee Decision}
    H -->|Approve| I[Admission Offer Sent]
    H -->|Reject| J[Application Rejected]
    H -->|Waitlist| K[Applicant Waitlisted]
```

## Additional Requirements

Applicants must submit all required documents by December 1, 2026.

The application fee is $50.

## Important Notes

The workflow above is fictional and intended exclusively for testing Mermaid diagram ingestion and retrieval.
