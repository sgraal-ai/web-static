# Sgraal

> The immune system for AI agent memory.

[![Live site](https://img.shields.io/badge/sgraal.com-Live-c9a962?style=flat-square)](https://sgraal.com)
[![Docs](https://img.shields.io/badge/Docs-Quickstart-c9a962?style=flat-square)](https://sgraal.com/docs/quickstart)

**[Live site →](https://sgraal.com)** · **[5-min Quickstart →](https://sgraal.com/docs/quickstart)** · **[Pricing →](https://sgraal.com/pricing)**

---

## What is Sgraal?

Sgraal is a production AI agent memory governance API. It returns `USE_MEMORY` / `WARN` / `ASK_USER` / `BLOCK` decisions on every memory access — so your agents act on memory only when it's safe to act on.

Built for AI engineers who need:

- **GDPR Article 5(1)(c) data minimization** with W3C Verifiable Credential proof
- **FDA-style Lyapunov stability proofs** for clinical / regulated AI agents
- **Drop-in Mem0 / Zep / Letta compatibility** — one environment-variable migration
- **Production-grade governance** — 2,981 tests, 86 scoring modules, 1,347+ heal actions shipped

## Quickstart

Python (Node.js and cURL also available at [/docs/quickstart](https://sgraal.com/docs/quickstart)):

```python
from sgraal import Sgraal

client = Sgraal(api_key="sg_demo_playground")
verdict = client.check(agent_id="my-agent", memory_state=[{"text": "user prefers email"}])
print(verdict.decision)  # USE_MEMORY / WARN / ASK_USER / BLOCK
```

The demo key `sg_demo_playground` works for `/v1/check` and `/v1/preflight` on the live API. Get your own key at [sgraal.com/pricing](https://sgraal.com/pricing).

## Features

### Live · Available today

- **Memory verdict API** — `POST /v1/check` — real-time `USE_MEMORY` / `WARN` / `ASK_USER` / `BLOCK` decisions
- **MVMem Certificate** — `POST /v1/certify/mvmem` — W3C VC GDPR Article 5(1)(c) data-minimization proofs
- **Convergence Proof PDF** — `POST /v1/proofs/convergence` — FDA-style Lyapunov stability documents
- **8 SDK packages** — Python, JavaScript / TypeScript, framework integrations

### Beta · Early Access

- Memory Time Machine — historical verdict replay
- Reverse Adversarial Generator — agent red-teaming
- In-Decision Human Veto — human-in-the-loop overrides

### Concept · Coming

- Sgraal Studio (web UI)
- Memory DNA forensics
- Agent FICO Score

See [sgraal.com](https://sgraal.com) for the full feature matrix with tier badges.

## SDK packages

| Package | Type | Install |
|---|---|---|
| [`sgraal`](https://pypi.org/project/sgraal/) | Python core | `pip install sgraal` |
| [`langchain-sgraal`](https://pypi.org/project/langchain-sgraal/) | LangChain integration | `pip install langchain-sgraal` |
| [`mem0-sgraal`](https://pypi.org/project/mem0-sgraal/) | Mem0 drop-in | `pip install mem0-sgraal` |
| [`openai-sgraal`](https://pypi.org/project/openai-sgraal/) | OpenAI Agents integration | `pip install openai-sgraal` |
| [`crewai-sgraal`](https://pypi.org/project/crewai-sgraal/) | CrewAI integration | `pip install crewai-sgraal` |
| [`autogen-sgraal`](https://pypi.org/project/autogen-sgraal/) | AutoGen integration | `pip install autogen-sgraal` |
| [`sgraal-rag`](https://pypi.org/project/sgraal-rag/) | RAG integration | `pip install sgraal-rag` |
| [`@sgraal/mcp`](https://www.npmjs.com/package/@sgraal/mcp) | MCP server (Claude Desktop) | `npm install @sgraal/mcp` |

## Open core model

Sgraal follows an open-core pattern:

- **Open (Apache 2.0)** — SDK clients, Edge mode (offline scoring), Proxy (Mem0 / Zep drop-in)
- **Hosted** — 86-module scoring engine, vaccine fleet, production calibration

The open SDK is sufficient for development, prototyping, and self-hosted Edge deployments. The hosted API at `api.sgraal.com` ships continuous improvement to scoring without requiring SDK updates.

See [/open-source](https://sgraal.com/open-source) for the full breakdown of what's open and what's hosted.

## Documentation

- [5-min Quickstart](https://sgraal.com/docs/quickstart) — Python / Node / cURL
- [API reference](https://sgraal.com/docs)
- [Threat model](https://sgraal.com/docs/threat-model)
- [Preflight ZK protocol](https://sgraal.com/docs/preflight-zk)
- [Scoring warnings catalog](https://sgraal.com/docs/scoring-warnings)
- [Memory ecosystem map](https://sgraal.com/memory-ecosystem-map) — how Sgraal fits with Mem0, Zep, Letta, LangSmith

## Company

Sgraal is being built by Peter Zsobrak at Zs-Consulting Kft. (Budapest).

- **Site** — [sgraal.com](https://sgraal.com)
- **Contact** — [hello@sgraal.com](mailto:hello@sgraal.com)
- **Pricing** — [sgraal.com/pricing](https://sgraal.com/pricing)
- **Design Partner Program** — [sgraal.com/comply](https://sgraal.com/comply) for compliance pilots

## License

This repository (`sgraal-ai/web-static`) contains the public source for the marketing site at [sgraal.com](https://sgraal.com). No formal `LICENSE` file ships at this time — content here is © 2026 Zs-Consulting Kft., all rights reserved.

The **Sgraal SDK** is licensed under **Apache 2.0** — see the individual SDK repositories for their license terms.

The **hosted scoring engine** at `api.sgraal.com` is proprietary.

---

⭐ **Star this repo** if you find Sgraal interesting — it helps others discover the project.
