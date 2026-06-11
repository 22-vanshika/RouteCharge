# PROJECT STANDARDS
## Bus Charging Scheduler — SDE Assessment

---

**Purpose**
This file is the single source of truth for every engineering decision made in this project.
Attach it to every prompt. Read the relevant section before creating a file, writing logic,
or making any structural or architectural choice. This is not a suggestion — it is the standard.

**Stack (locked)**
Language: Python · UI: Streamlit · Scheduling: Pure Python (in-memory) ·
Data Format: JSON scenario files · Hosting: Streamlit Community Cloud ·
No database. No auth. No external APIs. One repo, one process.

---

## SECTION 1 — ENGINEERING PRINCIPLES (SOLID)

These principles govern every decision. When convenience conflicts with a principle, the principle wins.

### 1.1 Single Responsibility
Every file, class, and function has exactly one reason to change and exactly one job to do.
If you find yourself writing "and" when describing what something does — split it into two things.
A function that both computes a charging plan and resolves station conflicts violates this.
A module that loads scenario data and also renders the UI violates this.
One concern. One unit.

### 1.2 Open / Closed
Every module is open for extension and closed for modification.
New behavior is added by extending — never by editing working, tested code.
Adding a new soft rule (e.g. priority buses, electricity cost) means adding a new rule definition — not rewriting the scoring engine.
Adding a new hard constraint means adding a new validator — not branching inside existing logic.
The scheduler engine itself never needs to change when new rules are introduced.

### 1.3 Liskov Substitution
Any implementation of a contract must be substitutable for that contract without breaking the system.
A mock scenario loader used in tests must behave identically to the real one.
A new soft rule implementation must be substitutable for any existing one without changing the engine.

### 1.4 Interface Segregation
No module depends on an interface it does not use.
The scheduler engine does not know about Streamlit. Streamlit does not know about scheduling internals.
A rule does not need to know about other rules. Each rule is evaluated independently on a clean interface.

### 1.5 Dependency Inversion
High-level modules never depend on low-level details directly.
The scheduler engine does not know which scenario file format is being used.
The UI does not know which scheduling algorithm is running.
Both depend on clean, stable interfaces — not on each other's internals.

---

## SECTION 2 — ARCHITECTURE

### 2.1 The Three-Layer Rule
The system has exactly three logical layers. They communicate in one direction only.

```
UI Layer  →  Scheduler Engine Layer  →  Data Layer
```

This direction is permanent. The data layer never calls the engine. The engine never calls the UI.

### 2.2 UI Layer (Streamlit)
**Only job:** render inputs, call the engine with a loaded scenario, display outputs.
**Permitted:** reading scenario files, calling engine functions, rendering tables and views.
**Forbidden:** scheduling logic of any kind, range validation, conflict resolution, rule scoring.

### 2.3 Scheduler Engine Layer
**Only job:** take a loaded scenario as input, produce a complete schedule as output.
**Permitted:** charging plan computation, conflict resolution, rule scoring, wait-time calculation.
**Forbidden:** file I/O, Streamlit imports, display formatting, reading environment variables.
**Key rule:** the engine is a pure function — same input always produces the same output.

### 2.4 Data Layer
**Only job:** define scenario structure, load scenario files, validate scenario shape.
**Permitted:** file reading, JSON parsing, schema validation, default value injection.
**Forbidden:** scheduling logic, UI calls, rule evaluation.

### 2.5 Rules as First-Class Objects
Soft rules are not scattered logic — they are discrete, named, independently-weighted objects.
Each rule receives a candidate schedule and returns a numeric score.
The engine collects all rule scores, applies their weights, and produces a final ranked decision.
Adding a rule means adding one new rule object. Nothing else changes.
Changing a weight means changing one value in the scenario's weight configuration. Nothing else changes.

---

## SECTION 3 — FILE AND FOLDER STRUCTURE

### 3.1 Top-Level Structure
```
bus-charging-scheduler/
├── app.py                   # Streamlit entry point — UI layer only
├── scheduler/               # Scheduler engine — all scheduling logic lives here
├── data/                    # Scenario JSON files — all 5 scenarios
├── tests/                   # Test files
├── requirements.txt         # All pip dependencies
├── README.md
└── ARCHITECTURE.md
```

No other top-level files or folders are created unless a new genuine concern is introduced.

### 3.2 Scheduler Package Structure
```
scheduler/
├── __init__.py
├── engine.py          # Orchestrates the full scheduling pipeline
├── planner.py         # Determines which stations each bus must stop at
├── resolver.py        # Resolves conflicts when multiple buses want the same charger
├── scorer.py          # Evaluates soft rules and computes weighted scores
├── rules/             # One file per soft rule
│   ├── __init__.py
│   ├── base.py        # Abstract base class for all rules
│   ├── individual.py  # Per-bus wait time rule
│   ├── operator.py    # Operator fairness rule
│   └── overall.py     # Total network time rule
├── models.py          # Pure data classes (Bus, Station, Schedule, ChargingStop, etc.)
├── loader.py          # Loads and validates scenario JSON files
└── validator.py       # Hard constraint validation (range rule, station order, etc.)
```

### 3.3 New File Rule
Before creating any new file, answer three questions:
1. Does a file already exist that owns this concern? If yes — extend that file, do not create a new one.
2. Which layer does this file belong to: UI, engine, data, rule, model, or utility?
3. Which module or concern owns this responsibility?

A file is created only when all three questions have clear, distinct answers.

### 3.4 New Folder Rule
A new folder is created only when a genuinely new coherent concern is introduced.
Folders are not created for tidiness, speculation, or because a single file feels isolated.

**Permitted folders:**
- `scheduler/` — the scheduling engine and all its sub-concerns
- `scheduler/rules/` — one file per soft rule definition
- `data/` — scenario JSON files only
- `tests/` — test files only

**Forbidden:** folders named `helpers`, `misc`, `utils`, `stuff`, or any vague catch-all name.
Shared utilities belong in `scheduler/models.py` or a clearly named file within `scheduler/`.

### 3.5 Data Folder Convention
```
data/
├── scenario_1.json    # Even spacing
├── scenario_2.json    # Bunched start
├── scenario_3.json    # Asymmetric load
├── scenario_4.json    # Operator-heavy
└── scenario_5.json    # Worst case convergence
```

Every scenario is a complete, self-contained JSON file.
The file encodes everything the engine needs: route, segments, stations, buses, weights, physical constants.
No scenario relies on hardcoded global constants in the codebase.

---

## SECTION 4 — DATA MODEL STANDARDS

### 4.1 Scenarios Are Self-Describing
A scenario file contains every value the engine needs to run. This means:
- Route definition (ordered list of stops with segment distances)
- Station definitions (which stops have chargers, how many chargers per station)
- Physical constants (battery range, charging time, bus speed)
- Soft rule weights (individual, operator, overall — and any future weights)
- Bus list (id, operator, direction, departure time)

Nothing is assumed from outside the scenario file.
This means changing segment distances, adding a station, or adding a new charger requires only a data change.

### 4.2 No Magic Numbers in Logic
Physical constants (range, charge time, speed) are never hardcoded in engine files.
They are always read from the loaded scenario.
If a value appears as a literal in scheduling logic, it is wrong — it belongs in the scenario data.

### 4.3 Time Representation
All times internally are represented as minutes since midnight (integer or float).
Departure times from scenario files are parsed from "HH:MM" format into this internal form once, at load time.
All engine computations use this internal form.
The UI layer is responsible for converting back to human-readable "HH:MM" for display.
No time formatting logic lives in the engine.

### 4.4 Pure Data Classes
All internal data structures (Bus, Station, ChargingStop, BusSchedule, ScenarioSchedule) are dataclasses or equivalent pure data containers.
They hold data. They do not contain business logic.
Methods on these classes are limited to simple computed properties (e.g. `arrival_time`).
Scheduling logic that operates on these objects belongs in the engine, not on the objects.

### 4.5 Immutability of Input
The scheduler engine never mutates the loaded scenario object.
A new output object is always constructed. The input is read-only.
This makes the engine safe to call multiple times with the same input without side effects.

---

## SECTION 5 — SCHEDULING ENGINE STANDARDS

### 5.1 The Engine Is a Pure Function
The entry point of the engine takes a `Scenario` object and returns a `ScenarioSchedule` object.
No global state. No file I/O. No print statements.
The same input always produces the same output.

### 5.2 Hard Rules Are Validated Separately
Hard constraint validation (range rule, station order, one charger at a time) is performed by `validator.py`.
The engine calls the validator before and after producing a schedule.
A hard rule violation raises a typed exception — it never silently passes.
Hard rules and soft rules are never mixed in the same function.

### 5.3 Soft Rules Are Weighted and Registered
Soft rules are registered as a list — not called directly by name in the engine.
The engine iterates over all registered rules, collects scores, applies weights, and makes decisions.
Adding a new soft rule means: create the rule file, register it in the rule list. The engine changes nothing.

### 5.4 Weights Are Scenario-Level Configuration
Weights live in the scenario's `weights` block.
The engine reads them at runtime. It never has default weights hardcoded.
Changing a weight for a scenario means editing one value in one JSON file.

### 5.5 Conflict Resolution Is Isolated
The logic that decides who charges first when two buses arrive at the same station at the same time lives entirely in `resolver.py`.
No other file makes this decision.
The resolver uses the soft rule scores to rank candidates. It does not recompute scores itself.

---

## SECTION 6 — CODE QUALITY STANDARDS

### 6.1 Function Length
No function exceeds 30 lines.
If a function approaches this limit, it is doing more than one thing — split it.

### 6.2 No Magic Values
No string literal for a station name, operator name, direction, or rule name appears more than once.
These values live in a constants file or in the scenario data itself.
Repeated literals are extracted before a second use ever appears.

### 6.3 Type Annotations
Every function signature has full type annotations on all parameters and the return value.
No `Any` type is used unless absolutely unavoidable, and such use is commented with justification.

### 6.4 DRY — Don't Repeat Yourself
If a value, a data transformation, or a block of logic appears in more than one place — it belongs in one shared place.
The moment you copy something for the second time, stop and extract it.

### 6.5 Naming Conventions
- Files: `snake_case.py`
- Classes: `PascalCase`
- Functions and variables: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Scenario JSON keys: `snake_case`

Names describe what a thing is or does — not how it does it.
`compute_charging_plan` is correct. `do_the_charging_stuff` is not.

### 6.6 Comment Philosophy
Comments explain why — not what.
A comment that restates what the code does provides no value.
A comment that explains why a non-obvious approach was taken, why an edge case requires special handling,
or why a particular rule interpretation was chosen provides high value.
Every non-trivial scheduling decision in the engine has a plain-language comment explaining the reasoning.

### 6.7 No Print Statements in Engine Code
The engine never prints to stdout.
Debug output is either a test assertion or a log — never a bare `print()` left in logic files.
The UI layer is responsible for all user-facing output.

---

## SECTION 7 — SCALABILITY STANDARDS

### 7.1 The Extension Test
Before finalizing any design decision, apply the extension test:
If tomorrow the spec adds a new rule, a new operator, a new station, a second charger at one station, a priority flag on buses, or a time-of-day electricity cost — does your design handle it through data or a small addition, without touching working engine code?
If the answer is no — redesign before writing code.

### 7.2 Weights Must Be Trivially Changeable
A reviewer must be able to change any weight by editing exactly one value in one JSON file.
If changing a weight requires touching Python code, the design is wrong.

### 7.3 Adding a Rule Must Not Touch the Engine
A new soft rule is implemented by:
1. Creating a new file in `scheduler/rules/`
2. Registering it in the rule list
3. Adding its weight key to the scenario JSON

No other file is modified. The engine is not touched.

### 7.4 Growing the World Through Data
The following changes must require only a data file change, no code changes:
- Adding a new bus
- Changing a departure time
- Changing a segment distance
- Adding a second charger at a station
- Adding a new station
- Adding a new operator
- Changing battery range or charging time

If any of these requires a code change, the data model is insufficiently expressive.

---

## SECTION 8 — DEVELOPMENT PRACTICES

### 8.1 Bottom-Up Build Order
The system is built in this exact order. A later layer is never started until the prior layer is complete and tested.

```
1. Data models (models.py)
2. Scenario loader and schema (loader.py)
3. Hard constraint validator (validator.py)
4. Charging plan generator (planner.py)
5. Soft rule definitions (rules/)
6. Scoring engine (scorer.py)
7. Conflict resolver (resolver.py)
8. Full engine orchestration (engine.py)
9. Streamlit UI (app.py)
```

This order exists because each layer depends only on what is below it.
Building UI before the engine produces untestable, tangled code.

### 8.2 Test Before You Build Up
Each layer is validated with at least a manual test or a unit test before the next layer begins.
A planner that produces invalid charging plans will silently corrupt everything built on top of it.

### 8.3 Commit Discipline
The codebase is in a working state at every commit.
A commit never leaves a module half-implemented.
Every commit message follows Conventional Commits: `feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `test:`
One commit per logical unit of work.

### 8.4 Branch Naming
`feature/`, `fix/`, `chore/`, `docs/`, `test/`, `refactor/` prefixes followed by a short hyphen-separated description.

---

## SECTION 9 — DOCUMENTATION STANDARDS

### 9.1 README Must Include
- What the project is and what problem it solves
- How to run it locally (three steps or fewer)
- How to change a weight (with the exact JSON field to edit)
- How to add a new rule (step-by-step, no code required in this doc)
- How to add a new scenario

### 9.2 ARCHITECTURE.md Must Include
- The scheduling framework chosen and why it is the right fit
- The data structure design and the reasoning behind each field
- A comprehensive list of anticipated future changes and how the design handles each one without code changes
- How to change a weight (with a concrete example)
- How to add a new rule (with a concrete example)
- All assumptions made where the spec was ambiguous

### 9.3 ARCHITECTURE.md Is the Strongest Eval Signal
The breadth and specificity of the anticipated changes section is the most important part of the submission.
It demonstrates that the engineer thought beyond today's spec.
Vague statements like "it's extensible" are not acceptable. Each anticipated change is named specifically.

---

## SECTION 10 — PRE-CHANGE CHECKLIST

Run this checklist before creating any file, writing any function, or considering any task complete.

**Architecture**
- Does this change belong to exactly one layer?
- Does the engine contain zero file I/O and zero Streamlit calls?
- Does the UI contain zero scheduling logic?
- Is every dependency passed in — never imported from a sibling module directly by name?

**Data Model**
- Is every physical constant read from the scenario — never hardcoded?
- Does the scenario file fully describe the world without assumptions from code?
- Is the new change expressible through data rather than code?

**Rules and Weights**
- Is the new rule a discrete, independently-scored object?
- Is its weight in the scenario JSON, not in Python code?
- Does adding this rule require zero changes to the engine?

**Code Quality**
- Are there zero magic string or number literals in logic files?
- Is every function under 30 lines?
- Does every function have full type annotations?
- Does every new class have exactly one responsibility?
- Are there zero `print()` calls in engine files?

**Scalability**
- Can this change be undone or varied purely through data?
- Does a new rule, bus, operator, or station require any code change?

**Documentation**
- Is every non-obvious decision commented with a "why"?
- Is the README still accurate after this change?
- Is ARCHITECTURE.md still accurate after this change?

**Commits**
- Does this commit follow Conventional Commits format?
- Does this commit represent exactly one logical unit of work?
- Is the project in a running state at this commit?

---

*This document defines the complete standard for this project.*
*Any deviation requires explicit written justification in the commit message.*
*When judgment and this document conflict — this document wins.*
