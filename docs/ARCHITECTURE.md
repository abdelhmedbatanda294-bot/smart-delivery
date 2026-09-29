# Smart Delivery & Logistics Management System
# System Architecture

## Architecture Overview

The system follows the Django MVT architecture with PostgreSQL
as the main database and Gemini API as the Agentic AI service.

```text
                    ┌──────────────────────┐
                    │       Browser        │
                    │ HTML / CSS / ES6 JS  │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │       Django         │
                    │      URL Router      │
                    └──────────┬───────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
              ▼                ▼                ▼
       ┌────────────┐   ┌────────────┐   ┌────────────┐
       │    Core    │   │  Delivery  │   │Authentication│
       │ Dashboard  │   │ Deliveries │   │ Login/RBAC │
       │   Drivers  │   │   Drivers  │   │   Users    │
       └──────┬─────┘   └──────┬─────┘   └──────┬─────┘
              │                │                │
              └────────────────┼────────────────┘
                               ▼
                    ┌──────────────────────┐
                    │      AI Agent        │
                    │ Gemini Function      │
                    │      Calling         │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │      AI Tools        │
                    │ Summary / Status     │
                    │ Permission Checks    │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │      PostgreSQL      │
                    │   Application Data   │
                    └──────────────────────┘