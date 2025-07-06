# pipeline/2_topology_builder/node_types_v2.py

from dataclasses import dataclass, field
from typing import Tuple, Optional, List, Any
import uuid

# Definierar en typ för 3D-vektorer för att göra koden tydligare.
Vector3D = Tuple[float, float, float]

@dataclass
class NodeInfo:
    """Grundläggande datastruktur för en nod i topologin."""
    coords: Vector3D
    id: str = field(default_factory=lambda: f"node_{uuid.uuid4().hex[:8]}")
    node_type: str = "UNKNOWN"
    requires_reducer: bool = False
    # Håller en referens till det "smarta" katalogobjektet för sin spec.
    assigned_spec: Optional[Any] = None 

@dataclass
class BendNodeInfo(NodeInfo):
    """Specifik data för en böj-nod."""
    node_type: str = "BEND"
    # Vinkeln i grader, beräknad av TopologyBuilder.
    angle: Optional[float] = None
    # De två normaliserade 3D-vektorerna som pekar från grannarna IN TILL denna nod.
    vectors: List[Vector3D] = field(default_factory=list)

@dataclass
class TeeNodeInfo(NodeInfo):
    """Specifik data för en T-korsning."""
    node_type: str = "TEE"
    # En lista med ID:n för de två noder som utgör huvudloppet ("the run").
    run_node_ids: List[str] = field(default_factory=list)
    # ID:t för den nod som utgör avsticket ("the branch").
    branch_node_id: Optional[str] = None

@dataclass
class EndpointNodeInfo(NodeInfo):
    """Specifik data för en ändpunkts-nod."""
    node_type: str = "ENDPOINT"
    # Typ av koppling, t.ex. "OPEN", "SMS_CLAMP". Sätts av TopologyBuilder.
    fitting_type: str = "OPEN"
    # Den utgående, normaliserade 3D-vektorn från denna ändpunkt.
    direction: Optional[Vector3D] = None
