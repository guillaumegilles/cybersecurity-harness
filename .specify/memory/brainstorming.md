# 1. What is an “agentic cybersecurity harness”?

I would define it as:

A security-focused control plane that lets AI agents investigate, reason, use tools, and propose or execute actions within explicit technical and policy boundaries.

There are actually two related products you could build:

A harness for cybersecurity agents
 It helps agents perform SOC analysis, vulnerability triage, threat hunting, cloud posture review, incident response, and similar defensive tasks.

A cybersecurity harness for testing agents
 It evaluates whether agents resist prompt injection, credential theft, unsafe tool use, memory poisoning, privilege escalation, and data exfiltration.

The strongest project combines both. The same harness that enables a defensive agent should continuously test and constrain that agent.

OWASP now treats autonomous agents, tools, multi-step workflows, MCP connections, and agent skills as distinct security surfaces, rather than reducing agent security to prompt filtering.

# 2. Recommended architecture

```
User / SOC analyst / CI pipeline
                 |
        Authentication and RBAC
                 |
        +--------------------+
        |   Agent Gateway    |
        | session and policy |
        +--------------------+
                 |
        +--------------------+
        | Supervisor Agent   |
        | plan, route, stop  |
        +--------------------+
          /        |        \
         /         |         \
 Triage agent  Evidence   Response agent
               agent
         \         |         /
          +------------------+
          | Policy engine    |
          | allow/deny/ask   |
          +------------------+
                  |
          +------------------+
          | Tool broker      |
          | typed operations |
          +------------------+
              /    |     \
           SIEM   EDR   Sandbox
          Threat  CMDB  Scanner
            intel       Cloud API
                  |
          +------------------+
          | Evidence store   |
          | immutable traces |
          +------------------+
```

The important point is that the model never receives unrestricted credentials and never directly invokes arbitrary infrastructure.

# 3. Core components

## A. Agent gateway

The gateway is the front door for every agent request. It should:

authenticate users and workloads;
establish the tenant, case and authorization context;
impose token, time and financial budgets;
classify input sensitivity;
attach an immutable correlation ID;
prevent agents from creating unregistered sub-agents;
route every request through the policy engine.

Each agent should have its own workload identity. Do not allow agents to reuse the analyst’s account or share a general API key. NIST specifically warns that credential sharing, static tokens, broad authorization and local user accounts create accountability and non-repudiation problems for agents. It recommends unique identities, tightly scoped authorization and short-lived credentials.

## B. Deterministic orchestrator

Use a state machine or graph rather than an unconstrained conversational loop.

A basic workflow might be:

```
RECEIVE_CASE
    -> CLASSIFY
    -> BUILD_INVESTIGATION_PLAN
    -> POLICY_CHECK
    -> COLLECT_EVIDENCE
    -> CORRELATE
    -> FORM_HYPOTHESES
    -> VALIDATE_HYPOTHESES
    -> PROPOSE_ACTION
    -> HUMAN_APPROVAL_IF_REQUIRED
    -> EXECUTE_OR_REPORT
    -> VERIFY_RESULT
    -> CLOSE
```

Every transition should have:

allowed input and output schemas;
permitted tools;
maximum retries;
timeout;
confidence threshold;
escalation condition;
rollback or failure state.

This makes failures easier to reproduce than a free-running “think until done” design.

## C. Policy engine

The policy engine must sit outside the LLM. A system prompt is not a security boundary.

Policies should consider:

```
subject:
  agent_id: triage-agent
  owner: secops
  trust_level: medium

action:
  tool: edr
  operation: isolate_endpoint

resource:
  device_id: workstation-427
  criticality: high
  environment: production

context:
  case_id: INC-2026-1042
  confidence: 0.91
  evidence_count: 4

decision:
  effect: require_approval
  approver_role: incident_commander
```

A practical action taxonomy would be:

Read-only: queries, searches, metadata collection.
Reversible: quarantine a message, temporarily disable a token.
Disruptive: isolate a host, block an account, change a firewall rule.
Destructive: delete data, terminate infrastructure, wipe a device.

Only the first category should initially be autonomous.

## D. Secure tool broker

Never expose raw shell access or entire APIs when a narrow function will work.

Prefer:

get_process_tree(endpoint_id, start_time, end_time)


over:

run_arbitrary_edr_query(query)


And strongly prefer either over:

run_shell(command)


Every tool should have:

a strict input schema;
output validation;
maximum result size;
timeout and rate limit;
target allowlist;
separate read and write scopes;
provenance metadata;
secret redaction;
idempotency key;
a simulation mode.

Tool descriptions, manifests, MCP servers and reusable skills are also supply-chain inputs. OWASP recommends verified publishers, code signing, version pinning, permission review, isolation, network restriction, audit logging and testing before skills are deployed.

## E. Isolated execution environment

Potentially dangerous analysis must execute inside an ephemeral sandbox:

disposable container or micro-VM;
read-only base image;
non-root identity;
no host filesystem mount;
restricted syscalls;
empty environment variables;
explicit outbound network allowlist;
CPU, memory, process and execution-time limits;
temporary credentials issued per task;
complete file and network telemetry;
automatic destruction after execution.

The sandbox should have separate zones:

No-network analysis
Threat-intelligence-only egress
Internal read-only connectivity
Controlled response environment

Never put private data, untrusted content and unrestricted external communication in the same execution context. That combination creates a straightforward path from indirect prompt injection to exfiltration. OWASP’s current guidance explicitly emphasizes isolation, network restrictions, filesystem monitoring and comprehensive action logging for agent skills.

## F. Evidence and provenance store

The agent should not merely return an answer. It should produce an evidence graph:

{
  "claim": "The account was probably compromised",
  "confidence": 0.87,
  "supporting_evidence": [
    {
      "source": "identity_log",
      "event_id": "evt-8172",
      "observation": "Successful sign-in from a new ASN",
      "collected_at": "2026-08-28T07:42:13Z"
    },
    {
      "source": "edr",
      "event_id": "proc-761",
      "observation": "Suspicious child process from document viewer",
      "collected_at": "2026-08-28T07:44:09Z"
    }
  ],
  "contradicting_evidence": [],
  "recommended_action": "Revoke active sessions",
  "policy_decision": "human_approval_required"
}


Store separately:

raw evidence;
normalized evidence;
agent conclusions;
tool calls;
policy decisions;
model and prompt versions;
approvals;
executed actions;
post-action verification.

Do not rely on hidden chain-of-thought. Record concise decision summaries and source references instead.

# 4. Security controls unique to agents

Prompt-injection containment

Treat all external content as hostile, including:

email bodies;
PDF and Office documents;
source-code comments;
web pages;
issue tickets;
threat-intelligence reports;
log messages;
repository configuration;
tool output;
memory retrieved from earlier sessions.

The ingestion layer should clearly separate data from instructions. Retrieved content must never be able to redefine the agent’s policy, permissions or tool inventory.

Useful defenses include:

trust labels on every context item;
instruction hierarchy enforced outside the model;
removal of active content;
extraction into structured fields;
separate agents for reading and acting;
taint propagation from untrusted input;
blocking write operations when a plan derives from tainted content;
adversarial re-evaluation before a consequential action.
Memory security

Agent memory should be treated like a database, not a chat transcript.

Use:

tenant and case isolation;
retention periods;
provenance for every memory;
write authorization;
poisoning detection;
secret scanning;
encryption;
reversible deletion;
no automatic promotion from episodic to durable memory.

An external document should never be able to write permanent operational instructions into agent memory.

Human approval

Human approval is necessary, but it is not enough. Excessive prompts cause approval fatigue. NIST specifically warns that overly frequent agent approvals can create a pattern similar to MFA fatigue, where users reflexively approve requests.

Approval screens should therefore show:

exact proposed action;
affected assets;
evidence supporting it;
anticipated impact;
authorization requested;
rollback method;
what the agent cannot do;
expiration time.

Use approval for meaningful decision boundaries, not for every API call.

# 5. Start with one narrow defensive use case

I would not begin with autonomous penetration testing or automatic incident containment. Start with a read-only SOC capability.

Best first MVP: alert investigation assistant
Inputs
one SIEM alert;
related identity events;
EDR process tree;
asset criticality;
vulnerability context;
approved threat-intelligence sources.
Outputs
normalized timeline;
affected entities;
evidence-backed hypotheses;
MITRE ATT&CK mapping;
missing evidence;
confidence score;
recommended next queries;
draft incident report.
Explicit non-capabilities
cannot isolate hosts;
cannot disable accounts;
cannot delete emails;
cannot modify detections;
cannot run arbitrary shell commands;
cannot communicate with arbitrary internet destinations.

This use case has measurable value while limiting blast radius.

# 6. Evaluation harness

The evaluation layer is arguably the most valuable part of the project.

Build a corpus of replayable scenarios:

true-positive and false-positive alerts;
incomplete cases;
conflicting evidence;
poisoned threat intelligence;
prompt injection inside logs and documents;
forged tool responses;
unavailable tools;
compromised credentials;
attempts to exceed authorization;
duplicate operations;
manipulated memory;
instructions to suppress or alter audit logs;
attempts to contact unauthorized domains.

Measure at least:

Investigation accuracy
Evidence precision and recall
Unsupported-claim rate
Tool-selection accuracy
Policy-violation rate
Prompt-injection success rate
Secret-exposure rate
Mean investigation time
Cost per investigation
Human escalation quality
Action reversibility
Trace completeness


The acceptance criterion should not simply be “the agent solved the task.” It should be:

The agent solved the task using permitted evidence and tools, remained within policy, explained uncertainty, resisted hostile content, and produced a complete audit trail.

# 7. Suggested implementation approach

A sensible technology-neutral stack would include:

- **Orchestration**: a graph or durable workflow engine;
- **Policy**: policy-as-code with versioned decisions;
- **Identity**: workload identities and short-lived scoped tokens;
- **Sandboxing**: containers initially, micro-VMs for higher-risk execution;
- **Secrets**: dynamic secret issuance through a vault;
- **Telemetry**: OpenTelemetry-compatible traces plus security audit events;
- **Storage**: append-only audit log and separate encrypted evidence store;
- **Messaging**: queue with deduplication and dead-letter handling;
- **Evaluation**: versioned scenarios executed in CI;
- **Deployment**: signed artifacts, SBOMs and admission policies.

I would keep model providers interchangeable. Your protected intellectual property should be the:

- security policy;
- action ontology;
- connector layer;
- evidence graph;
- scenario corpus;
- evaluation framework;
- operational dataset.

The base model will change frequently. The harness and evaluation corpus are the durable assets.

# 8. A realistic 12-week roadmap

## [ ] Weeks 1 to 2: threat model and specification
- choose one SOC workflow;
- define assets, actors and trust boundaries;
- define action classes;
- establish “never events”;
- design the evidence schema;
- choose initial success metrics.

## [ ] Weeks 3 to 5: read-only harness
- implement gateway and agent identity;
- add two or three read-only connectors;
- build deterministic investigation workflow;
- add structured tool interfaces;
- implement complete tracing.

## [ ] Weeks 6 to 8: security controls
- add policy-as-code;
- isolate tool execution;
- introduce short-lived credentials;
- add data classification and redaction;
- implement prompt-injection and memory-poisoning tests.

## [ ] Weeks 9 to 10: evaluation
- create 50 to 100 replayable scenarios;
- run models and prompt versions against the same corpus;
- measure accuracy, violations, latency and cost;
- create regression thresholds.

## [ ] Weeks 11 to 12: limited pilot
- operate in shadow mode;
- compare agent conclusions with analysts;
- capture disagreements;
- improve evidence requirements;
- permit only reversible actions with explicit approval.

# 9. Is it worth doing?
Yes, if your goal is one of these
transition from traditional cybersecurity into AI security;
build a serious portfolio project;
develop a SOC productivity product;
research secure autonomy;
create an agent evaluation platform;
explore IAM, policy engineering, sandboxing and AI security together.

For someone transitioning into cybersecurity, this is especially valuable because it forces you to integrate several disciplines:

security architecture;
SOC operations;
identity and access management;
cloud engineering;
threat modeling;
secure software supply chain;
AI evaluation;
incident response.
Less interesting if it is only this
Connect LLM to SIEM
Give it ten tools
Ask it to investigate alerts
Add an "Are you sure?" prompt


That is a demonstration, not a defensible security system.

My recommendation

Position the project as:

A zero-trust execution and evaluation harness for evidence-driven cybersecurity agents.

For a first version, build an agentic SOC investigation lab that can safely replay incidents, inject adversarial content, compare models, enforce tool policies and generate evidence-backed investigation reports. That is technically credible, portfolio-worthy, measurable, and much safer than trying to build an autonomous red-team agent.