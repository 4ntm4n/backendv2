# Spara denna kod i: pipeline/shared/types.py
from typing import Dict, Any, TypeAlias, List

# Genom att placera denna i en delad fil kan både centerline_builder
# och plan_adjuster importera den utan att skapa cirkulära beroenden.

# Ett enskilt objekt i en byggplan, t.ex. en böj eller ett rakt rör.
BuildPlanItem: TypeAlias = Dict[str, Any]

# En komplett byggplan, vilket är en lista av BuildPlanItems.
BuildPlan: TypeAlias = List[BuildPlanItem]