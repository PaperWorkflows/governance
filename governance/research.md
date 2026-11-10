# Research Mode Rules

## Scope

This file defines the research mode execution rules. Research mode covers: material retrieval and analysis, code development, data collection, statistical analysis, and experiment execution.

## Rules

### PF-R1 研究执行授权

- Each research task must be bound to: paper identity, absolute root path, input snapshot, role, applicable rules, allowed write scope, expected files, budget, outputs, and acceptance criteria.
- Research tasks cannot span papers or modify governance infrastructure.
- Raw materials are read-only. Formal results, evidence, logs, and reports are in the paper workspace. Temporary materials go to `temp/P<ID>-<DATE>-<TITLE>-<AUTHOR>/TASK-<NNNN>/`.

### PF-R2 实验设计

- Experiments must define: problem, data split, metrics, baseline, budget, and failure criteria upfront.
- Record: data source and version, license, inclusion/exclusion rules, preprocessing, code version, environment, run commands, parameters, raw logs, and result generation entry.
- Limited-access data must state acquisition conditions and reproduction limits. Do not falsely claim public availability.

### PF-R3 基线设置

- Baselines must use reasonable settings and comparable resources. Report hyperparameter tuning methods.
- Machine learning research must check train-test leakage, randomness, repeated runs, and necessary ablations.
- System research must report workload, hardware, throughput, latency, resource consumption, and failures.

### PF-R4 统计与报告

- State sample size, denominator, statistical unit, missing values and outlier handling. Independent samples vs repeated measures must be separated.
- Report mean, dispersion, intervals, or test methods appropriate to data nature. Do not force one test on all research.
- When using "significant", clarify statistical vs practical significance. State method, assumptions, and multiple comparison treatment.
- Body text and figure values must come from the same result source. Rounding and units must be consistent.

### PF-R5 数据来源声明

- Distinguish measured, computed, simulated, synthetic, estimated, and illustrative results.
- Autonomous experiments must actually execute authorized research plans and save execution evidence.
- Legal external data may be input but must not be claimed as self-collected. Clearly state input source and result nature.

### PF-R6 代码与复现

- All code used in experiments must be preserved in `experiments/code/`. Record code version, dependencies, and run commands.
- Raw data stays in `experiments/data/` and is never modified in place. Cleaning produces new files with source references.
- Run logs go to `experiments/logs/` with timestamps, parameters, and exit codes.

### PF-R7 实验记录

- Each experiment run produces a record entry in `experiments/record.yaml` with: experiment ID, date, environment ref, command, parameters, input files, output files, checksums, status, and notes.
- Failed runs are recorded with failure reason and partial outputs. Do not delete failure records.

### PF-R8 环境与隔离

- Experiment execution must declare an isolation tier (E0/E1/E2/E3). Tier declaration is mandatory; "already isolated" without specification is invalid.
- E0: host read-only (no install, no third-party code execution, no writes).
- E1: container isolation with digest-pinned image. Network denied by default.
- E2: local isolation (bwrap) with read-only root, independent net/pid/ipc namespaces, no host sockets, masked credentials, writable root only under project temp.
- E3: host execution (restricted). Requires per-execution independent pre-approval by a subagent not involved in the execution. Record in task.yaml isolation_exemption.
- Network in isolation is denied by default. Mirror pull, dependency fetch, and external service access require separate authorization with source and checksum.
