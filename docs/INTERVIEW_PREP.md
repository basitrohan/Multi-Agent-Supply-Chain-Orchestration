# Interview Prep: How to Talk About This Project

This document exists for one purpose: so you can talk about this project **confidently and quickly**, even with limited prep time. It maps every phrase in your resume bullet to the actual code, gives you a 60-second summary, and prepares you for the questions most likely to come up.

## Your resume bullet, restated

> Architected an autonomous agentic system using LangGraph to manage multi-step supply chain decision-making, replacing legacy static ETL pipelines. Implemented FastAPI microservices to trigger agentic workflows that simulate supply chain stress tests, generating predictive YoY performance reports via AWS Bedrock.

---

## The 60-second summary (say this if asked "walk me through this project")

> "I built a multi-agent system that runs supply chain stress tests. Instead of a fixed pipeline that always does the same steps, I used LangGraph to build a graph of five agents — data ingestion, risk assessment, simulation, forecasting, and report generation — where the path through the graph actually changes based on what's discovered. The clearest example: if the risk assessment comes back high and the first simulation pass shows a high stockout probability, the simulation agent automatically loops back and re-runs itself with more Monte Carlo iterations before it trusts the result enough to move forward. That's something a static linear pipeline just can't do.
>
> The whole thing is exposed through a FastAPI microservice — one POST endpoint triggers the entire workflow and returns a structured result plus a generated executive report. The report itself is written by an LLM on AWS Bedrock, but I made sure the LLM only writes the narrative — every number in the report comes from deterministic code, not from the model, which matters a lot for something a business would actually act on.
>
> I also built it so it runs fully offline with a mock LLM if there's no AWS account configured, which made it easier to develop and test without burning cloud credits, and the switch between mock and real Bedrock is a single environment variable — no code changes."

---

## Phrase-by-phrase mapping

| Resume phrase | Where it lives in the code | What to say about it |
|---|---|---|
| "Architected an autonomous agentic system" | `app/agents/graph.py` — the `StateGraph` with conditional edges | The system *decides its own next step* based on what it finds — see the simulation retry loop below. That's the "autonomous" part: no human in the loop deciding whether to re-run anything. |
| "using LangGraph" | `app/agents/graph.py`, all files in `app/agents/` | Five nodes, registered with `add_node`; routing decided by a shared `route_next()` function reading a `next_agent` field every agent writes into a shared state object. |
| "multi-step supply chain decision-making" | The full 5-agent pipeline: ingest → risk → simulate → forecast → report | Each step is a genuine decision point, not just a data transform — especially risk assessment (is this dangerous?) and simulation (do I trust this result enough to proceed?). |
| "replacing legacy static ETL pipelines" | Contrast described in `docs/ARCHITECTURE.md` → "The problem this replaces" | A static pipeline always runs the same steps. This system conditionally skips ahead to an error report on bad data, and conditionally loops back to re-simulate on high risk — neither of which a fixed script does. |
| "Implemented FastAPI microservices" | `app/main.py`, `app/api/routes.py` | `POST /api/v1/stress-test` triggers the whole workflow; `GET /api/v1/reports` and `/health` are separate concerns, cleanly split. Routes are thin — all logic lives in the service layer. |
| "to trigger agentic workflows" | `app/services/orchestration_service.py: run_stress_test()` | This is the one function that bridges the HTTP layer and the LangGraph graph — call `.invoke()` on the compiled graph and shape the result. |
| "that simulate supply chain stress tests" | `app/services/simulation_engine.py` | Monte Carlo simulation: random lead-time delays (shaped by each supplier's reliability score) checked against inventory buffer days, across N iterations, producing stockout probability and revenue-impact statistics including a P90 tail metric. |
| "generating predictive YoY performance reports" | `app/agents/forecasting_agent.py` | Spreads the simulated revenue impact across a 12-month horizon with a disruption window and recovery taper, producing baseline vs. stressed year-over-year growth percentages. |
| "via AWS Bedrock" | `app/services/llm_service.py: BedrockLLMClient` | Uses `boto3`'s `bedrock-runtime` client and the unified `converse` API. Falls back automatically to an offline mock (`MockLLMClient`) if no AWS credentials are configured, via a single factory function, `get_llm_client()`. |

**A point worth raising even though it's not literally in the resume bullet:** the project also has 37 passing tests at 95% coverage and a GitHub Actions CI pipeline (`.github/workflows/ci.yml`) that lints, format-checks, tests, and Docker-builds-and-smoke-tests on every push. Bringing this up unprompted signals that you think about software quality as part of the job, not as an afterthought — strong for a senior-leaning AI Engineer role.

---

## Likely follow-up questions (and how to answer them)

**"Why LangGraph instead of just LangChain, or just writing plain Python functions?"**
> "LangChain's chains are linear — step A always leads to step B. I needed conditional branching and a loop: if the data fails validation, skip straight to an error exit; if the simulation result looks unreliable given how severe the risk is, re-run the simulation with more iterations before moving on. LangGraph models the workflow as an actual graph with conditional edges, which is the right data structure for that. I could have hand-rolled this with if/else in plain Python, but LangGraph gives me a shared state object with defined merge semantics across nodes, and a clear visual/structural representation of the workflow that's easier to extend and reason about as more agents get added."

**"How does the system decide when to retry the simulation?"**
> "The risk assessment agent computes a 0-to-1 risk score from three factors: how severe the requested disruption is, what fraction of suppliers are in the affected region, and what fraction of SKUs have less buffer stock than the disruption is expected to last. If that score is at or above a threshold — 0.65 by default — and the first simulation pass shows more than a 50% stockout probability, the simulation agent re-runs itself with double the Monte Carlo iterations, up to a max retry count, so I don't get an infinite loop."

**"Why is the risk scoring rule-based instead of using an LLM?"**
> "Explainability. If a risk score is going to drive a re-simulation decision, I want to be able to point at the exact formula and defend it, not say 'the model decided.' Not every agent in an agentic system has to call an LLM — agents are fundamentally about decision-making and orchestration. The LLM is one tool I use specifically where natural-language generation is the actual task, which is the final report-writing step."

**"What happens if AWS Bedrock isn't available, or the call fails?"**
> "Two layers of fallback. First, at startup, if there are no AWS credentials in the environment, the system automatically uses an offline mock LLM client instead — it's a small template engine that reads the same structured data the real prompt would and renders a genuinely readable markdown report from it. Second, even if real Bedrock IS configured, if an individual API call fails for some reason — bad credentials, model not enabled in that region, throttling — I catch that and fall back to the mock for that one call rather than crashing the whole stress-test run."

**"How do you make sure the LLM doesn't hallucinate the numbers in the report?"**
> "The agent that calls the LLM builds a prompt with all the actual numbers — risk score, simulation stats, forecast — as a structured JSON block, and the system prompt explicitly instructs the model to only narrate those numbers, not invent or recompute them. The model's job is strictly the prose; every figure traces back to deterministic code upstream."

**"Is this actually tested?"**
> "Yes — 37 tests: unit tests for the simulation math and the data validation logic in isolation, unit tests for each individual agent node (since each one is just a plain function, `state -> dict`, they're trivial to test without running the whole graph), a few full end-to-end integration tests that run the real graph including the escalation/retry path, and API-level tests using FastAPI's TestClient. Coverage sits at 95%. There's also a GitHub Actions CI pipeline that runs lint, format-checking, the full test suite, and a Docker build-plus-smoke-test on every push — so it's not just 'tests exist,' it's 'tests are enforced automatically before anything merges.'"

**"What does your CI/CD pipeline actually check?"**
> "Three jobs, in order: ruff for linting, black in check-mode for formatting consistency, then the full pytest suite with coverage — all running with `USE_MOCK_LLM=true` so CI never needs real AWS credentials. After that passes, a second job builds the actual Docker image and runs a smoke test: starts the container, waits for it to come up, and curls the health endpoint to confirm it actually serves traffic, not just that it builds. That smoke test is the part I'd highlight — a lot of CI setups stop at 'the image built,' which doesn't prove the container actually runs correctly."

**"Is there a UI, or is this API-only?"**
> "I built a small React frontend on top of the same FastAPI backend, intentionally kept as a separate app that talks to the API over HTTP rather than bundled into the backend — that's the standard separation, and it means the backend stays equally usable from a UI, a CLI, or another service calling it directly. The interesting design decision was the agent pipeline visualization: instead of a generic spinner, I render the five agents as a vertical checklist that 'stamps' each one as it completes in real time, and if the Simulation agent escalates into a retry, that shows up as a visible tag right on that step. It's a small thing, but it's the one piece of UI that actually communicates what makes this system agentic rather than a static form-to-report tool."

**"How would you scale this for production?"**
> "Right now a stress test runs synchronously within one HTTP request — fine for a demo, but a long stress test under load would block. I'd add a task queue, return a `run_id` immediately from the POST endpoint, and add a separate endpoint to poll status or fetch the result once it's done. The orchestration service is already structured so that change wouldn't touch any agent logic at all — it's a clean seam. I'd also move the supplier/inventory data out of local JSON files into a real database, which again only touches one file, the data loader."

**"What was the hardest part of building this?"**
> "Getting the LangGraph state design right. LangGraph requires node names and state field names to not collide — I actually hit that directly: I originally named a state field `risk_assessment`, same as the node name, and LangGraph raised a `ValueError` at graph-compile time. I renamed the result fields to things like `risk_assessment_result` to keep node names and data fields cleanly separated. It's a small thing, but it taught me to think of 'the node' and 'the data that node produces' as genuinely separate concepts, which is a useful distinction for any graph-based system."

---

## If they ask you to draw the architecture on a whiteboard

Reproduce this shape — five boxes in a line, with one loop-back arrow on the third box (Simulation), and one early exit arrow from the first box (Data Ingestion) straight to "End":

```
[Data Ingestion] --ok--> [Risk Assessment] --> [Simulation] <--loop (retry)--
        |                                            |
      bad data                                    accepted
        v                                            v
      [END]                                   [Forecasting] --> [Report Gen] --> [END]
```

Full versions are saved as `diagrams/langgraph_workflow.svg` and `diagrams/system_architecture.svg` if you want to review them beforehand.

---

## Things to genuinely double check before the interview

- [ ] Run `python scripts/run_demo.py --severity 0.95 --days 45` once yourself, right before the interview, so you've personally seen the retry loop trigger and printed.
- [ ] Open one generated report in `data/reports/` and skim it so you can describe its structure from memory.
- [ ] Re-read `app/agents/simulation_agent.py` once — it's the single most important file to understand cold, since it's the crux of the "agentic" claim.
- [ ] Know the one-sentence trade-off for each major design decision (see `docs/ARCHITECTURE.md` → "Design decisions and trade-offs") — being asked "why didn't you do X instead" and having a ready, honest answer is a strong signal.
