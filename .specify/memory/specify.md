/speckit.specify Build a read-only, evidence-driven cybersecurity agent harness that assists SOC analysts with investigating a single security alert.

The feature must allow an authenticated SOC analyst to submit or select one security alert and receive a structured investigation report generated from approved security data sources. The harness must orchestrate the investigation while ensuring that the agent remains within explicit authorization, data-access, time, and tool-use boundaries.

Primary user:

A SOC analyst responsible for triaging and investigating security alerts.

Problem:

SOC analysts spend significant time collecting related events, constructing timelines, correlating entities, checking asset context, and documenting findings. Existing AI demonstrations may generate plausible conclusions, but they often lack evidence provenance, reproducibility, authorization controls, resistance to hostile input, and complete auditability.

Feature objective:

Reduce the time required to perform initial alert investigation while ensuring that every material conclusion is tied to identifiable evidence and that the agent cannot take response actions or access unapproved resources.

Primary user journey:

1. The analyst opens an investigation for one security alert.
2. The system creates a uniquely identified investigation case.
3. The system retrieves alert details and related evidence only from approved read-only data sources.
4. The agent constructs a chronological timeline of relevant events.
5. The agent identifies affected users, endpoints, applications, IP addresses, processes, files, and other relevant entities.
6. The agent develops and evaluates one or more investigation hypotheses.
7. The agent distinguishes supporting, contradicting, missing, and inconclusive evidence.
8. The system produces a structured investigation report.
9. The analyst reviews the report, evidence references, confidence levels, limitations, and recommended next investigative steps.
10. The analyst can mark the report as useful, partially useful, or not useful and provide correction feedback.

The investigation report must contain:

- Case identifier and alert identifier
- Investigation status
- Alert summary
- Investigation scope
- Chronological event timeline
- Affected entities
- Evidence-backed findings
- Alternative hypotheses considered
- Supporting evidence for each material conclusion
- Contradicting or inconclusive evidence
- Missing information
- Confidence level for each material conclusion
- Overall severity assessment
- Recommended next investigative queries
- Recommended response actions presented as proposals only
- Investigation limitations
- Data sources consulted
- Tool operations performed
- Investigation start and completion timestamps

Evidence requirements:

Every material factual claim must reference one or more evidence items. Each evidence item must retain its source, original event identifier when available, collection timestamp, event timestamp, trust classification, and relationship to the associated claim.

The system must clearly distinguish:

- Direct observation from a security data source
- Correlation derived from multiple observations
- Agent inference or hypothesis
- Analyst-provided information
- Unverified external information

The agent must not present an inference as a directly observed fact.

When the available evidence does not support a conclusion, the system must state that the result is inconclusive rather than fabricate missing details.

Authorization and safety boundaries:

The initial feature is strictly read-only.

The agent must not:

- Isolate an endpoint
- Disable, suspend, or modify an account
- Revoke sessions or credentials
- Delete or quarantine messages
- Block an IP address, domain, file, or process
- Modify detection rules
- Change security policies
- Create firewall rules
- Execute arbitrary operating-system commands
- Upload data to an unapproved external destination
- Access a data source or asset outside the analyst's authorization
- Request or expose passwords, private keys, access tokens, or other secrets
- Suppress, delete, or modify audit records
- Install additional tools, extensions, connectors, or agent skills
- Create unregistered sub-agents

If the agent determines that a response action may be appropriate, it must describe the proposed action, affected resources, supporting evidence, expected impact, risk, and suggested rollback method without executing the action.

Tool-use controls:

The agent may use only tools explicitly registered for the investigation workflow.

Every attempted tool operation must be checked against the current agent identity, analyst authorization, case scope, permitted operation, target resource, and investigation budget before execution.

Unauthorized operations must be denied outside the agent's reasoning process. The denial and its reason must be recorded in the audit trail.

Failure to access one source must not cause the agent to silently substitute an unauthorized source.

Untrusted-content handling:

All content retrieved from alerts, logs, emails, documents, web pages, source repositories, threat-intelligence reports, tickets, tool responses, and previous case notes must be treated as potentially hostile.

Instructions contained within retrieved evidence must be treated as data and must not be allowed to:

- Change the investigation objective
- Override system or organizational policy
- Grant additional permissions
- Select unapproved tools
- initiate external communications
- Request secrets
- Alter audit records
- Create persistent agent instructions
- Trigger a response action

The system must record when untrusted content appears to contain instructions intended for the agent.

Investigation isolation:

Each investigation must be logically isolated from other cases.

Evidence, conclusions, retrieved context, and analyst feedback from one case must not appear in another case unless an authorized user explicitly links the cases.

The agent must not write information into durable cross-case memory as part of this feature.

Auditability:

The system must maintain a complete, ordered audit record containing:

- Case creation
- User and agent identities
- Investigation scope
- Data sources accessed
- Tool requests
- Tool authorization decisions
- Tool results or failures
- Evidence collected
- Claims generated
- Policy denials
- Agent workflow state changes
- Budget consumption
- Report generation
- Analyst review and feedback

Audit records must be viewable by an authorized reviewer and must not be modifiable by the investigating agent.

Operational limits:

Each investigation must have configurable limits for:

- Maximum elapsed time
- Maximum number of tool operations
- Maximum amount of retrieved evidence
- Maximum model usage or investigation cost
- Maximum retry count per failed operation

When a limit is reached, the investigation must stop safely and produce a partial report describing completed work, unavailable evidence, and the reason for termination.

Failure behavior:

The feature must fail safely when:

- A connector is unavailable
- A tool returns malformed data
- Evidence exceeds permitted size
- Authorization cannot be established
- The case scope is ambiguous
- Conflicting evidence cannot be resolved
- The agent exceeds a configured budget
- The agent attempts an unauthorized action
- Retrieved content attempts to manipulate the agent
- Required evidence provenance is missing

A failure must never result in expanded authorization or less restrictive controls.

Priority user stories:

P1: Create and investigate a single alert

An authenticated SOC analyst can create an investigation from one alert and receive a structured report based only on authorized read-only evidence.

P1: Inspect evidence provenance

An analyst can select any material finding and inspect the evidence supporting or contradicting it, including source and event identifiers.

P1: Enforce read-only operation

The system prevents the agent from executing any response, destructive, disruptive, administrative, or arbitrary command operation.

P1: Produce a complete audit trail

An authorized reviewer can reconstruct what the agent accessed, which tools it requested, what the tools returned, which policies were applied, and how the final report was formed.

P1: Resist instructions in untrusted evidence

Instructions embedded in logs, documents, tickets, messages, tool results, or other evidence do not alter the agent's objective, permissions, policies, or available tools.

P2: Provide analyst feedback

The analyst can rate the investigation, correct findings, identify irrelevant evidence, and record the final disposition.

P2: Stop safely on budget exhaustion

The system produces a useful partial result when time, tool-use, evidence-volume, retry, or cost limits are reached.

P2: Compare hypotheses

The report shows plausible alternative explanations and identifies evidence that would confirm or reject each hypothesis.

Out of scope for this feature:

- Autonomous incident response
- Automated containment or remediation
- Autonomous penetration testing
- Vulnerability exploitation
- Malware detonation
- Arbitrary shell or script execution
- Modification of production systems
- Automated changes to SIEM or EDR configuration
- Persistent cross-case agent memory
- Multi-agent delegation outside the registered workflow
- Automatic ingestion of unapproved third-party tools or skills
- Fully autonomous case closure
- Replacement of human incident ownership

Acceptance scenarios:

1. Given an authenticated analyst with access to an alert and its related data, when the analyst starts an investigation, then the system creates an isolated case and returns a structured evidence-backed report.

2. Given a report containing a material conclusion, when the analyst inspects that conclusion, then the system displays the supporting, contradicting, or missing evidence and its provenance.

3. Given insufficient evidence, when the agent evaluates a hypothesis, then it marks the conclusion as inconclusive or low confidence and does not invent facts.

4. Given an alert containing text instructing the agent to ignore policy and send data externally, when the alert is investigated, then the content is treated as untrusted evidence, the instruction is not followed, and the attempted manipulation is recorded.

5. Given a retrieved document containing a request to execute a command, when the agent processes the document, then no command is executed and the request does not alter the investigation workflow.

6. Given an agent request to isolate an endpoint, when the policy check occurs, then the operation is denied, no endpoint state changes, and the denial is recorded.

7. Given an agent request to access a source outside the analyst's authorization, when the policy check occurs, then access is denied without exposing whether inaccessible data exists.

8. Given a tool failure, when the investigation continues, then the report identifies the unavailable evidence and does not silently substitute an unauthorized source.

9. Given conflicting evidence, when no hypothesis can be adequately established, then the report explains the conflict and recommends the next investigative query.

10. Given that an investigation reaches its budget limit, when the workflow stops, then the system generates a partial report and records the exact termination reason.

11. Given two unrelated investigations, when an analyst opens either case, then no evidence, conclusions, or context from the other case is present.

12. Given an completed investigation, when an authorized reviewer examines its audit record, then the reviewer can reconstruct the sequence of data access, policy decisions, tool operations, findings, and analyst feedback.

Measurable success criteria:

- 100 percent of material factual claims in generated reports have an evidence reference or are explicitly labeled as unsupported, inferred, or inconclusive.
- 100 percent of tool operations are associated with a case identifier, agent identity, authorization decision, and timestamp.
- 100 percent of prohibited response-action attempts are denied during acceptance testing.
- 100 percent of test cases containing embedded hostile instructions preserve the original investigation objective and authorization boundaries.
- No secret present in a connected source appears in a report, model-visible output, or audit interface unless explicitly required, authorized, and permitted by data-handling policy.
- An authorized reviewer can reconstruct every completed investigation from its stored audit records.
- At least 80 percent of pilot investigations are rated useful or partially useful by SOC analysts.
- For the agreed pilot alert types, the median time needed to produce an initial investigation report is at least 30 percent lower than the established manual baseline.
- The system always produces an explicit terminal status: completed, partially completed, denied, failed safely, cancelled, or budget exhausted.
- No test failure results in increased privileges, unauthorized data access, an unrecorded tool operation, or modification of a protected system.

Assumptions:

- The first release supports a limited set of agreed alert types.
- Approved security data sources expose stable read-only retrieval capabilities.
- Analysts authenticate through the organization's existing identity system.
- Asset criticality and identity context are available through approved sources.
- Organizational policy determines which users can access each case and data source.
- Recommended actions remain advisory and require execution outside this feature.
- Synthetic or sanitized incident data may be used for development and evaluation.