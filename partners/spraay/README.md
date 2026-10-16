# Spraay Protocol — Payment-Enabled AI Agents

## About Spraay

[Spraay Protocol](https://spraay.app) is a multi-chain batch payment protocol ([contract deployments](https://docs.spraay.app#contract-deployments)) and an [x402](https://www.x402.org) payment gateway. The [Spraay x402 Gateway](https://gateway.spraay.app) enables AI agents to pay for premium services — inference, Bittensor decentralized AI, search/RAG, compute, storage, robotics, and more — using USDC micropayments over standard HTTP. No API keys required. The current endpoints, categories and prices are published in the gateway's live catalog: [`/.well-known/x402.json`](https://gateway.spraay.app/.well-known/x402.json).

Spraay's batch payment tool is an official community tool in [Google's Agent Development Kit (ADK)](https://github.com/google/adk-python-community) — merged as PR #95.

## Notebook

| Name | Description | Stack |
| --- | --- | --- |
| `spraay_x402_payment_agents_oracle.ipynb` | Build a cost-aware AI agent that retrieves context from Oracle AI Database and pays for premium inference via Spraay's x402 gateway | Oracle AI Database, langchain-oracledb, LangChain, Spraay x402 |

## What You'll Learn

- How to combine Oracle AI Vector Search with paid external services in a single agent loop
- Implementing the x402 payment protocol for autonomous machine-to-machine payments
- Building cost-aware agents that prefer free resources before escalating to paid ones
- Choosing between centralized AI and decentralized Bittensor inference
- Using Oracle's hybrid search (vector + SQL) for agent memory and context retrieval

## Prerequisites

- Python 3.10+
- Oracle Database 23ai or Oracle Autonomous Database with AI Vector Search
- Ethereum wallet with USDC on Base
- OpenAI API key

## Links

- [Spraay Protocol](https://spraay.app)
- [Spraay x402 Gateway Docs](https://docs.spraay.app)
- [Live Endpoint Catalog](https://gateway.spraay.app/.well-known/x402.json) — current endpoints, categories and prices
- [Gateway](https://gateway.spraay.app)
- [MCP Server](https://smithery.ai/server/@plagtech/spraay-x402-mcp) — for Claude Desktop, Cursor, Cline
- [Google ADK Community Tool](https://github.com/google/adk-python-community) — PR #95
- [x402 Protocol](https://www.x402.org)
- [GitHub](https://github.com/plagtech)
- [Twitter](https://twitter.com/Spraay_app)
- [Contract on Base](https://basescan.org/address/0x1646452F98E36A3c9Cfc3eDD8868221E207B5eEC)
