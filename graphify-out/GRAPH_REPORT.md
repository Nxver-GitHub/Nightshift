# Graph Report - Project-Sunday  (2026-08-14)

## Corpus Check
- Corpus is ~26,816 words - fits in a single context window. You may not need a graph.

## Summary
- 285 nodes · 484 edges · 27 communities (22 shown, 5 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 65 edges (avg confidence: 0.65)
- Token cost: 314,373 input · 34,929 output

## Community Hubs (Navigation)
- Block Catalog & Install Commands
- Kit Method, Interview & Acme Example
- CRM CLI Implementation
- Goals CLI Implementation
- Prospection CLI Implementation
- Content Agents CLI Implementation
- Safety Gates & Scheduling
- Taskrunner Kanban Core
- Session Cycle Process Control
- Outbound Prospecting Role
- Dashboard Read-Only Server
- Goals Block & Autonomy Contract
- Email Operator Block
- Health Monitoring Block
- Healthcheck Probe Implementation
- Health Journal Logger
- Task Update Command
- Email Operator State Store
- Sessions Block & Context Reset
- Taskrunner Launcher Scripts
- Task Creation Command
- Task Listing Command
- Email Operator Runner Script
- Scheduled Task Runner Script
- Taskrunner Start Script
- Taskrunner Stop Script

## God Nodes (most connected - your core abstractions)
1. `build_parser()` - 14 edges
2. `build_parser()` - 12 edges
3. `Blocks catalog` - 11 edges
4. `goal agent skill` - 11 edges
5. `build_parser()` - 10 edges
6. `taskrunner block` - 10 edges
7. `now()` - 9 edges
8. `log_event()` - 9 edges
9. `The Company Brain — rules every brain obeys` - 9 edges
10. `build_parser()` - 8 edges

## Surprising Connections (you probably didn't know these)
- `CRM event log (every mutation logs an event)` --semantically_similar_to--> `State as of block`  [INFERRED] [semantically similar]
  blocks/crm/block.md → START-HERE.md
- `No secret in git — ever` --semantically_similar_to--> `Brain lives in a sibling folder`  [INFERRED] [semantically similar]
  blocks/connectors.md → START-HERE.md
- `Agents as Roles (forward-looking role skills layer)` --semantically_similar_to--> `Monthly Retainer Offer (€600–900, three flows)`  [INFERRED] [semantically similar]
  kit/ontology.md → examples/acme-brain/acme/notes/positioning.md
- `Acme Flows — Brain Routing Hub` --semantically_similar_to--> `Brain Routing Hub Template (CLAUDE.md)`  [INFERRED] [semantically similar]
  examples/acme-brain/CLAUDE.md → kit/templates/CLAUDE.md
- `Acme Flows — Company Brain (entry point)` --semantically_similar_to--> `Company Brain Entry Point Template (main_brain.md)`  [INFERRED] [semantically similar]
  examples/acme-brain/main_brain.md → kit/templates/main_brain.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Sunday installation flow: command → runbook → interview → brain** — _claude_commands_sunday_command, start_here_installer_runbook, start_here_founding_interview, start_here_brain_scaffold, readme_company_brain [EXTRACTED 1.00]
- **Command Center assembly from blocks** — _claude_commands_sunday_assemble_command, blocks_readme_blocks_catalog, blocks_readme_consolidation_flow, blocks_readme_command_center, blocks_readme_review_mode [EXTRACTED 1.00]
- **Dashboard aggregates taskrunner, CRM, and brain state** — blocks_dashboard_block, blocks_dashboard_code_index_load, changelog_taskrunner_block, blocks_crm_crm_db, readme_company_brain [EXTRACTED 1.00]
- **The owner's-yes safety floor across blocks** — blocks_taskrunner_skill_taskrunner_finalization_gate, blocks_taskrunner_skill_taskrunner_reversible_boundary, blocks_email_operator_skill_email_operator_never_irreversible, blocks_prospection_block_validation_gate, blocks_scheduled_tasks_block_review_mode, blocks_health_block_red_becomes_ticket [EXTRACTED 1.00]
- **Taskrunner as the shared execution hub** — blocks_taskrunner_block_add_task_py, blocks_taskrunner_block_tasks_json, blocks_email_operator_skill_email_operator_triage_rule, blocks_goals_skill_goal_goal_agent, blocks_health_block_healthcheck_py [EXTRACTED 1.00]
- **Keeping agents running: periodic schedule vs persistent loop with resets** — blocks_scheduled_tasks_block_run_scheduled_sh, blocks_scheduled_tasks_code_templates_cron_cron_template, blocks_taskrunner_block_start_taskrunner_sh, blocks_sessions_block_session_cycle_py, blocks_scheduled_tasks_block_persistent_vs_periodic [INFERRED 0.85]
- **Company Brain scaffold — the template set generated per brain** — kit_templates_claude_routing_hub_template, kit_templates_main_brain_company_brain_template, kit_templates_entity_main_entity_profile, kit_templates_entity_notes_people_people_template, kit_templates_entity_notes_positioning_positioning_template, kit_templates_entity_notes_tools_tools_template [EXTRACTED 1.00]
- **Acme Flows worked example — a filled instance of the scaffold** — examples_acme_brain_claude_acme_flows_routing_hub, examples_acme_brain_main_brain_acme_flows_company_brain, examples_acme_brain_acme_main_acme_flows, examples_acme_brain_acme_notes_people_robin_vega, examples_acme_brain_acme_notes_positioning_acme_flows_positioning, examples_acme_brain_acme_notes_tools_tools_and_accounts, examples_acme_brain_acme_logs_2026_08_founding_log_entry, examples_acme_brain_clients_readme_clients_folder [EXTRACTED 1.00]
- **Interview → ontology → templates → generated brain pipeline** — kit_interview_company_founding_interview, kit_ontology_company_brain_method, kit_templates_main_brain_company_brain_template, examples_acme_brain_main_brain_acme_flows_company_brain [INFERRED 0.85]

## Communities (27 total, 5 thin omitted)

### Community 0 - "Block Catalog & Install Commands"
Cohesion: 0.06
Nodes (51): /sunday-assemble command, /sunday command, Block anatomy template, Composio (recommended connector), Connector agnosticism, No secret in git — ever, content-agents block, Content pipeline idea→draft→ready→posted (+43 more)

### Community 1 - "Kit Method, Interview & Acme Example"
Cohesion: 0.12
Nodes (33): Acme Flows Log — 2026-08 (founding entry), Acme Flows (company entity), Dr. Lena Fischer (warm prospect, Ghent practice), Robin Vega (founder, solo), Acme Flows Positioning & Offer, Anti-Position — Not a Software Subscription, ICP — Independent Belgian Dental Practices (1–3 chairs), Monthly Retainer Offer (€600–900, three flows) (+25 more)

### Community 2 - "CRM CLI Implementation"
Cohesion: 0.23
Nodes (21): build_parser(), cmd_add_company(), cmd_add_contact(), cmd_init(), cmd_list(), cmd_note(), cmd_project_add(), cmd_project_move() (+13 more)

### Community 3 - "Goals CLI Implementation"
Cohesion: 0.26
Nodes (19): build_parser(), cmd_activate(), cmd_add(), cmd_done(), cmd_due(), cmd_list(), cmd_notify(), cmd_plan() (+11 more)

### Community 4 - "Prospection CLI Implementation"
Cohesion: 0.22
Nodes (16): build_parser(), cmd_add_step(), cmd_approve(), cmd_create_sequence(), cmd_due_today(), cmd_mark_sent(), cmd_reply_received(), cmd_show() (+8 more)

### Community 5 - "Content Agents CLI Implementation"
Cohesion: 0.32
Nodes (13): build_parser(), cmd_add(), cmd_list(), cmd_mark_posted(), cmd_set(), cmd_show(), cmd_stats(), find() (+5 more)

### Community 6 - "Safety Gates & Scheduling"
Cohesion: 0.18
Nodes (14): Never an irreversible action on your own, healthcheck.json exemptions, Health install & schedule runbook, Prospection validation gate, due-today approved batch, Review-mode scheduled runs, run-scheduled.sh generic runner, scheduled-tasks block (+6 more)

### Community 7 - "Taskrunner Kanban Core"
Cohesion: 0.29
Nodes (11): The triage rule: simple or multi-step, add_task.py, list_tasks.py, taskrunner block, tasks.json kanban, update_task.py, Claim before work, Message-triggered task contract (+3 more)

### Community 8 - "Session Cycle Process Control"
Cohesion: 0.31
Nodes (9): find(), info(), main(), _ps_started(), Real process start time (`ps -o lstart=`). Format e.g. 'Sat Aug  3 17:27:45 2026, The `claude` process for this agent (not the caffeinate wrapper), or None., runs_of(), _runs_read() (+1 more)

### Community 9 - "Outbound Prospecting Role"
Cohesion: 0.22
Nodes (10): Connector-agnostic email integration, Composio recommended connector, Email operator install & operate runbook, prospection block, prospection.py sequence queue, Prospection install & operate runbook, Proven prospecting script library, ICP qualification against positioning.md (+2 more)

### Community 10 - "Dashboard Read-Only Server"
Cohesion: 0.33
Nodes (4): Handler, read_brain(), read_crm(), read_tasks()

### Community 11 - "Goals Block & Autonomy Contract"
Cohesion: 0.29
Nodes (8): goal.py goal store, goals block, Goals install & operate runbook, 48h auto-activate delay, The autonomy contract, goal agent skill, Multi-channel by default, One goal per session guardrail

### Community 12 - "Email Operator Block"
Cohesion: 0.33
Nodes (7): email-operator block, run-operator.sh headless run, state.py already-handled tracker, email-operator skill (inbox triage role), End-of-run report, Sender identity verification before disclosure, Two escalation levels (normal / high)

### Community 13 - "Health Monitoring Block"
Cohesion: 0.33
Nodes (7): Mandatory honest measure, health block, health-log.py journal, healthcheck.py, A red signal becomes a taskrunner ticket, Unknown-not-red, always exit 0 discipline, The runner judges completion, not the delegate

### Community 14 - "Healthcheck Probe Implementation"
Cohesion: 0.52
Nodes (6): cfg(), check_crm(), check_stale_claims(), check_tasks_json(), main(), parse_ts()

### Community 15 - "Health Journal Logger"
Cohesion: 0.67
Nodes (5): _append(), main(), now(), _read(), today()

### Community 16 - "Task Update Command"
Cohesion: 0.53
Nodes (5): main(), now(), parse_due(), clears the due date; otherwise strict YYYY-MM-DD. Raises on anything else, BEFOR, resolve_tasks()

### Community 17 - "Email Operator State Store"
Cohesion: 0.70
Nodes (4): load(), main(), path(), save()

### Community 18 - "Sessions Block & Context Reset"
Cohesion: 0.40
Nodes (5): Context saturation and session reset, list-sessions.py attributed session finder, session-cycle.py run counter and reset, sessions block, Handoff first, reset second

### Community 19 - "Taskrunner Launcher Scripts"
Cohesion: 0.50
Nodes (4): Persistent loop vs periodic trade-off, Sessions install & wire runbook, start-taskrunner.sh launcher, .taskrunner.on on/off flag

### Community 20 - "Task Creation Command"
Cohesion: 0.83
Nodes (3): main(), now(), resolve_tasks()

## Knowledge Gaps
- **12 isolated node(s):** `run-operator.sh script`, `run-scheduled.sh script`, `start-taskrunner.sh script`, `stop-taskrunner.sh script`, `/sunday command` (+7 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **5 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `taskrunner block` connect `Taskrunner Kanban Core` to `Taskrunner Launcher Scripts`, `Outbound Prospecting Role`, `Goals Block & Autonomy Contract`, `Email Operator Block`?**
  _High betweenness centrality (0.014) - this node is a cross-community bridge._
- **Why does `goal agent skill` connect `Goals Block & Autonomy Contract` to `Safety Gates & Scheduling`, `Taskrunner Kanban Core`, `Email Operator Block`, `Health Monitoring Block`, `Sessions Block & Context Reset`?**
  _High betweenness centrality (0.013) - this node is a cross-community bridge._
- **Are the 12 inferred relationships involving `build_parser()` (e.g. with `cmd_add_company()` and `cmd_add_contact()`) actually correct?**
  _`build_parser()` has 12 INFERRED edges - model-reasoned connections that need verification._
- **Are the 10 inferred relationships involving `build_parser()` (e.g. with `cmd_activate()` and `cmd_add()`) actually correct?**
  _`build_parser()` has 10 INFERRED edges - model-reasoned connections that need verification._
- **Are the 8 inferred relationships involving `build_parser()` (e.g. with `cmd_add_step()` and `cmd_approve()`) actually correct?**
  _`build_parser()` has 8 INFERRED edges - model-reasoned connections that need verification._
- **What connects `run-operator.sh script`, `run-scheduled.sh script`, `start-taskrunner.sh script` to the rest of the system?**
  _12 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Block Catalog & Install Commands` be split into smaller, more focused modules?**
  _Cohesion score 0.05656108597285068 - nodes in this community are weakly interconnected._