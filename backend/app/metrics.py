from prometheus_client import Counter

EQUIPMENT_CREATED = Counter(
    "equipment_created_total",
    "Number of successfully created equipment items",
)

EMPLOYEES_CREATED = Counter(
    "employees_created_total",
    "Number of successfully created employees",
)

EQUIPMENT_ASSIGNMENTS = Counter(
    "equipment_assignments_total",
    "Number of successful equipment assignments",
)

EQUIPMENT_RETURNS = Counter(
    "equipment_returns_total",
    "Number of completed equipment returns",
)

EQUIPMENT_ASSIGNMENTS_FAILS = Counter(
    "equipment_assignments_failures_total",
    "Number of equipment assignments failed due to technical errors",
)

EQUIPMENT_RETURNS_FAILS = Counter(
    "equipment_returns_failures_total",
    "Number of equipment returns failed due to technical errors",
)

EQUIPMENT_CREATED_FAILS = Counter(
    "equipment_created_failures_total",
    "Number of equipment creations failed due to technical errors",
)
