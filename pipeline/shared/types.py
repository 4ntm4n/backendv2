# Spara denna kod i: backendv2/shared/types.py
from typing import Dict, Any, TypeAlias

# Genom att placera denna i en delad fil kan både build_planner
# och plan_adjuster importera den utan att skapa cirkulära beroenden.
BuildPlanItem: TypeAlias = Dict[str, Any]

