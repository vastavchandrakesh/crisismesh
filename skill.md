You are the lead full-stack engineer for our 24-hour hackathon project.

PROJECT NAME:
CrisisMesh

PROJECT:
AI-Powered Audio Intelligence for Faster Disaster Victim Detection

IMPORTANT:
Build the COMPLETE WORKING FULL-STACK MVP now.
Do not just give me architecture, pseudocode, explanations, TODOs, or mock screens.
Create the actual project files, install dependencies, implement the backend, frontend, database, AI/audio pipeline, APIs, offline queue simulation, and demo flow.

We have 24 hours and are a first-time hackathon team.
Therefore:
- prioritize a reliable working vertical slice over unnecessary complexity
- use simple, explainable algorithms
- avoid overengineering
- avoid features that cannot be demonstrated locally
- do not build production-grade emergency infrastructure
- do not claim unsupported capabilities
- everything important must actually work

==================================================
1. CORE IDEA — DO NOT CHANGE THIS
==================================================

During disasters, victims may be physically close to rescuers but difficult to locate.

The problem is not simply communication.

The problem is that responders can receive many noisy, duplicated, low-confidence and time-sensitive signals and cannot manually inspect every possible audio source.

CrisisMesh is a software-first emergency intelligence layer.

Core pipeline:

AFFECTED AREA
      ↓
USER CONSENT
      ↓
EMERGENCY AUDIO CAPTURE
      ↓
AUDIO AI
      ↓
DISTRESS EVENT
      ↓
CONFIDENCE SCORE
      ↓
LOCATION + TIME + EVIDENCE
      ↓
INCIDENT FUSION / DUPLICATE CLUSTERING
      ↓
PRIORITIZED RESPONDER INCIDENT
      ↓
RESPONDER DASHBOARD

The system supports responders.
It does NOT automatically make rescue decisions.

==================================================
2. PRIVACY / MICROPHONE RULE — CRITICAL
==================================================

Never implement secret microphone activation.

Never silently turn on a microphone.

Never bypass Android/iOS permission systems.

The prototype must use:

NORMAL MODE:
- App installed
- Permissions clearly explained
- No emergency audio processing
- Privacy controls visible
- System inactive

EMERGENCY MODE:
- Authorized disaster/emergency scenario is activated
- User receives a prominent explanation/request
- User explicitly opts in
- Only then may the prototype capture/process audio
- Store minimum necessary metadata

The UI must clearly communicate microphone status.

Example:

MICROPHONE
● Inactive

Then after opt-in:

MICROPHONE
● Emergency monitoring active
Stop

For hackathon/demo purposes, make the emergency activation easy to trigger using a DEMO MODE / simulated disaster zone.

Do not pretend the app has government authority.
Do not pretend it can force participation.

==================================================
3. WHAT MUST ACTUALLY WORK
==================================================

Build these working components:

A. MOBILE / DEVICE SIMULATOR
B. AUDIO AI SERVICE
C. BACKEND API
D. DATABASE
E. INCIDENT FUSION ENGINE
F. RESPONDER DASHBOARD
G. OFFLINE QUEUE
H. DEMO SIMULATION

We need an end-to-end demo:

1. Activate disaster demo
2. Test device enters emergency mode
3. User opts in
4. Generate/capture audio
5. AI analyzes it
6. Distress event is created
7. Confidence score calculated
8. Location/time metadata attached
9. Multiple nearby events are clustered
10. One incident appears on responder dashboard
11. Simulate internet loss
12. Event enters local queue
13. Connectivity returns
14. Event synchronizes
15. Dashboard updates

This entire flow must work.

==================================================
4. RECOMMENDED STACK
==================================================

Use a stack optimized for speed.

FRONTEND:
React + Vite
TypeScript
Tailwind CSS
Leaflet or another lightweight map library

BACKEND:
Python
FastAPI
WebSocket support

DATABASE:
SQLite for the MVP

AI:
Python
librosa / soundfile / numpy if useful
A lightweight explainable classifier

Do NOT depend on a huge ML model that requires massive downloads.

If an actual ML model is unreliable or difficult to run locally:
implement a lightweight audio-event classifier using:
- audio features
- keyword detection
- simple rules
- confidence scoring

The important thing is that the demo works.

You may optionally support Whisper or another speech-to-text model ONLY if it can run reliably in the local environment.

Do not make the whole application dependent on an external paid API.

==================================================
5. PROJECT STRUCTURE
==================================================

Create something similar to:

crisismesh/
│
├── backend/
│ ├── app/
│ │ ├── main.py
│ │ ├── config.py
│ │ ├── database.py
│ │ ├── models/
│ │ ├── schemas/
│ │ ├── api/
│ │ ├── services/
│ │ │ ├── audio_ai.py
│ │ │ ├── confidence.py
│ │ │ ├── incident_fusion.py
│ │ │ ├── offline_sync.py
│ │ │ └── location.py
│ │ └── websocket.py
│ ├── tests/
│ └── requirements.txt
│
├── frontend/
│ ├── src/
│ │ ├── components/
│ │ ├── pages/
│ │ ├── services/
│ │ ├── hooks/
│ │ ├── types/
│ │ └── App.tsx
│ └── package.json
│
├── mobile/
│ └── [only if practical]
│
├── demo/
│ ├── sample_audio/
│ └── scenarios/
│
├── README.md
├── docker-compose.yml
└── .env.example

You may change the structure if there is a better practical solution.

==================================================
6. AUDIO AI
==================================================

Implement a lightweight audio intelligence service.

Input:
short audio clip

Output:

{
  "event_type": "HELP",
  "confidence": 0.94,
  "evidence": [
    "possible distress speech",
    "keyword detected"
  ]
}

Supported event classes for MVP:

HELP
TRAPPED
CRYING
SHOUTING
KNOCKING
MEDICAL_DISTRESS
UNKNOWN
NO_DISTRESS

Do NOT claim the classifier can perfectly understand victims.

The result must be:

candidate event + confidence

not:

"this person is definitely trapped."

Create a clean service abstraction so the AI model can later be replaced.

Example:

AudioAnalyzer.analyze(audio_file)

returns:

event_type
confidence
evidence
duration
timestamp

==================================================
7. CONFIDENCE SCORE
==================================================

Implement an explainable confidence score.

Use factors such as:

AI audio confidence
freshness
location confidence
corroboration
evidence quality

Example conceptual formula:

final_score =
0.40 * audio_confidence
+ 0.20 * freshness
+ 0.15 * location_confidence
+ 0.20 * corroboration
+ 0.05 * evidence_quality

Normalize to 0–100.

Make the weights configurable.

Do NOT pretend these weights are scientifically validated.

Display:

Confidence: 92%

and explain why:

Audio evidence: 94
Freshness: 100
Location: 90
Corroboration: 85

==================================================
8. FRESHNESS
==================================================

Every report needs:

created_at
updated_at

Implement freshness decay.

Example:

A 1-minute-old report should be much more relevant than a 2-hour-old report.

Implement a simple configurable decay function.

Display:

Fresh
Recent
Aging
Stale

Do not permanently treat an old report as current.

==================================================
9. LOCATION CONFIDENCE
==================================================

Every event should have:

latitude
longitude
location_accuracy
source_device_id

For the MVP, location can be simulated.

Display location confidence separately.

Example:

Location confidence: 88%

Do not expose unnecessary personal information.

==================================================
10. CORROBORATION
==================================================

This is one of the important differentiators.

Suppose:

Phone A → "HELP"
Phone B → "I am trapped"
Phone C → knocking

If they are:
- geographically close
- temporally close
- semantically related

then combine them into one incident.

Example:

3 related signals
→ 1 incident

Do not simply count every report.

Create an incident fusion service.

Possible clustering criteria:

distance threshold
time threshold
event similarity
confidence

Make thresholds configurable.

==================================================
11. INCIDENT OBJECT
==================================================

Create something like:

Incident:

id
status
priority
confidence
latitude
longitude
radius
created_at
updated_at
last_signal_at
signal_count
unique_device_count
event_types
evidence
verification_status

Possible status:

NEW
INVESTIGATING
VERIFIED
RESOLVED
STALE

Possible priority:

CRITICAL
HIGH
MEDIUM
LOW

==================================================
12. DUPLICATE SUPPRESSION
==================================================

Example:

300 reports around the same school

should NOT automatically become:

300 incidents.

The system should identify that multiple signals may belong to one incident.

Display:

12 signals
4 devices
1 incident

This is a core demo feature.

==================================================
13. RESPONDER DASHBOARD
==================================================

Build a polished dashboard.

Main sections:

TOP:
CrisisMesh
DISASTER RESPONSE MODE
connection status
system status

LEFT:
Incident list

CENTER:
Map

RIGHT:
Selected incident details

Incident card example:

CRITICAL
Possible survivor cluster

Confidence 92%

Sector A-12

3 related devices

Last signal:
18 seconds ago

Evidence:
HELP
TRAPPED
KNOCKING

Status:
Needs verification

Buttons:

Verify
Assign
Resolve
Mark stale

==================================================
14. MAP
==================================================

Use Leaflet.

Show:

incident markers
severity
confidence
affected zone
selected incident

Marker colors:

RED = critical
ORANGE = high
YELLOW = medium
GREEN = low/verified

Clicking marker opens incident details.

Use simulated coordinates for the hackathon.

Do NOT require Google Maps API keys.

==================================================
15. LIVE UPDATES
==================================================

Use WebSockets.

When a new event is created:

backend
→ incident fusion
→ dashboard WebSocket
→ dashboard updates

No page refresh should be required.

If WebSockets become unreliable during implementation, implement polling fallback.

==================================================
16. OFFLINE MODE
==================================================

This is important.

We need to demonstrate:

CONNECTED:

Device
→ Backend
→ Dashboard

CONNECTION LOST:

Device
→ Local queue

Then:

CONNECTION RESTORED

Local queue
→ Backend
→ Dashboard

Implement a local event queue.

Each queued event should contain:

event_id
created_at
payload
status
retry_count

Possible:

PENDING
SYNCING
SYNCED
FAILED

Provide a DEMO button:

SIMULATE CONNECTION LOSS

and:

RESTORE CONNECTION

When offline:
- new events are stored locally
- UI clearly shows OFFLINE
- no fake "delivered" status

When restored:
- queued events sync automatically

==================================================
17. MESH / RELAY
==================================================

Do NOT spend the hackathon trying to implement a real multi-hop Bluetooth mesh unless it is trivial.

Instead implement a software relay simulation.

Example:

Device A
↓
Relay Device B
↓
Relay Device C
↓
Responder Gateway

Create a "Relay Simulation" screen.

Show:

Device A
● OFFLINE
↓
Device B
● RELAY
↓
Device C
● RELAY
↓
Gateway
● ONLINE

A test event should travel through the simulated relay chain.

Clearly label this:

"Prototype relay simulation"

not:

"Production mesh network."

Keep the architecture modular so BLE/Wi-Fi Direct can replace the simulator later.

==================================================
18. PRIVACY
==================================================

Build privacy into the UI.

Include:

Consent status
Microphone status
Data retention status
Device identifier pseudonymization
Minimal metadata
Stop monitoring button

Do not display:
real phone numbers
real names
unnecessary personal data

Use:

DEVICE-7F3A

instead of:

Vishnu's iPhone

For the demo, generate synthetic device IDs.

==================================================
19. RESPONDER AUTHENTICATION
==================================================

Implement simple demo authentication.

Roles:

RESPONDER
ADMIN

Do not build a complicated identity system.

Demo credentials can be documented in README.

Make clear:

"Demo authentication only."

==================================================
20. DEMO MODE
==================================================

This is extremely important.

Create a Demo Control panel.

Buttons:

START DISASTER
GENERATE HELP EVENT
GENERATE TRAPPED EVENT
GENERATE KNOCKING EVENT
GENERATE NOISE
CREATE DUPLICATE REPORTS
CREATE CORROBORATING REPORTS
SIMULATE CONNECTION LOSS
RESTORE CONNECTION
CLEAR INCIDENTS
RESET DEMO

This allows us to demonstrate the entire system without depending on real disaster conditions.

==================================================
21. DEMO SCENARIO
==================================================

Create a built-in scenario:

DISASTER:
Building collapse

LOCATION:
Sector A-12

Generate:

Device A:
HELP

Device B:
I AM TRAPPED

Device C:
KNOCKING

Device D:
NO DISTRESS

The system should produce:

ONE INCIDENT

Example:

CRITICAL
Possible survivor cluster

Confidence: 92%

Signals: 3
Devices: 3

Evidence:
HELP
TRAPPED
KNOCKING

Device D should NOT significantly increase the confidence.

Then:

SIMULATE CONNECTION LOSS

Generate another event.

It should enter:

LOCAL QUEUE

Then:

RESTORE CONNECTION

It synchronizes and appears on dashboard.

This is our primary judging demo.

==================================================
22. API
==================================================

Implement clean REST endpoints.

Examples:

POST /api/auth/login

POST /api/disaster/start

GET /api/disaster/status

POST /api/events

POST /api/events/analyze

GET /api/events

GET /api/incidents

GET /api/incidents/{id}

POST /api/incidents/{id}/verify

POST /api/incidents/{id}/resolve

POST /api/demo/generate-event

POST /api/demo/generate-correlated-events

POST /api/demo/simulate-offline

POST /api/demo/restore-connection

GET /api/system/status

WebSocket:

/ws/incidents

Add OpenAPI documentation through FastAPI.

==================================================
23. DATABASE
==================================================

Use SQLite.

Tables:

users
devices
disasters
events
incidents
incident_events
sync_queue
audit_logs

Add indexes for:

timestamp
latitude
longitude
incident_id
status

Use SQLAlchemy or another lightweight ORM.

==================================================
24. AUDIT LOG
==================================================

Every important action should generate an audit entry.

Examples:

CONSENT_GRANTED
EMERGENCY_MODE_STARTED
AUDIO_ANALYZED
EVENT_CREATED
INCIDENT_CREATED
INCIDENT_MERGED
INCIDENT_VERIFIED
INCIDENT_RESOLVED
SYNC_STARTED
SYNC_COMPLETED

This makes the system more explainable.

==================================================
25. UI DESIGN
==================================================

Make the dashboard look like a serious emergency-response product.

Do NOT make it look like a generic CRUD application.

Use:

light beige / off-white base
dark charcoal text
teal primary accent
orange warning
red critical
blue information

Clean cards
clear hierarchy
large confidence numbers
clear status badges
map
incident timeline

Responsive desktop-first layout.

The dashboard should be understandable within 5 seconds.

==================================================
26. SAFETY / CLAIMS
==================================================

Do not claim:

100% detection
guaranteed rescue
perfect AI
automatic victim identification
silent microphone activation
government authorization
real emergency deployment
production-ready mesh

Use language like:

"candidate distress signal"
"confidence score"
"prototype"
"demo"
"responder verification"

==================================================
27. TESTING
==================================================

Create tests for:

confidence calculation
freshness decay
incident clustering
duplicate suppression
offline queue
sync
API endpoints
authentication
incident state changes

Also create one end-to-end demo test.

Run the tests.

Fix failures.

==================================================
28. README
==================================================

Write a strong README containing:

What CrisisMesh is
Problem
Solution
Architecture
Tech stack
Setup
Environment variables
How to run backend
How to run frontend
How to run demo
Demo credentials
Demo scenario
API overview
Privacy model
Offline behavior
Known limitations
Future extensions

Be honest about limitations.

==================================================
29. DEVELOPMENT RULES
==================================================

IMPORTANT:

DO NOT stop after creating a plan.

DO NOT ask me what to build next.

DO NOT give me 20 options.

Make reasonable engineering decisions yourself.

Build the project.

Run it.

Test it.

Fix errors.

Then inspect the UI and improve obvious problems.

Keep dependencies minimal.

Avoid unnecessary libraries.

Avoid unnecessary animations.

Avoid unnecessary authentication complexity.

Avoid cloud services unless absolutely necessary.

Prefer local development.

Everything should run with:

backend:
uvicorn app.main:app --reload

frontend:
npm run dev

Provide a single convenient startup method if possible.

==================================================
30. FINAL ACCEPTANCE CRITERIA
==================================================

The project is complete only when I can demonstrate:

[ ] Login
[ ] Start disaster scenario
[ ] Enter emergency mode
[ ] Explicit consent
[ ] Audio event generation
[ ] AI/event classification
[ ] Confidence score
[ ] Freshness score
[ ] Location confidence
[ ] Corroboration
[ ] Incident creation
[ ] Duplicate clustering
[ ] Responder dashboard
[ ] Map
[ ] Live incident updates
[ ] Offline queue
[ ] Connection loss simulation
[ ] Connection restoration
[ ] Sync
[ ] Relay simulation
[ ] Privacy controls
[ ] Audit logs
[ ] Demo scenario
[ ] Tests passing

==================================================
31. EXECUTION INSTRUCTIONS
==================================================

Start by inspecting the current directory.

If a project already exists:
reuse it where practical instead of rebuilding unnecessarily.

If no project exists:
initialize it.

Then implement the system incrementally.

After each major component:
run tests/build.

At the end:

1. Start backend
2. Start frontend
3. Run tests
4. Verify API
5. Verify demo scenario
6. Fix errors
7. Check browser console
8. Check backend logs
9. Make UI fixes
10. Give me concise instructions for running the final system

Do not waste tokens explaining every implementation detail to me.

Spend your effort writing and testing the actual code.

IMPORTANT:
If something cannot realistically be implemented in 24 hours, implement the smallest honest working simulation and clearly isolate it behind an interface for future replacement.

The goal is:

A WORKING, DEMONSTRABLE, POLISHED 24-HOUR HACKATHON MVP.

NOT a theoretical architecture.