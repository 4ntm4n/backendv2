import pytest
import networkx as nx
import math
from typing import List, Tuple, Dict, Any

# Importera klasser från andra moduler
from components_catalog.loader import CatalogLoader
from pipeline.topology_builder.node_types_v2 import NodeInfo, EndpointNodeInfo, BendNodeInfo
from pipeline.plan_adjuster.adjuster import PlanAdjuster
from pipeline.shared.types import BuildPlan

# --- Fixtures (Testdata) ---

@pytest.fixture
def catalog():
    """Laddar den riktiga katalogen för att ha tillgång till riktiga komponentdata."""
    return CatalogLoader("./components_catalog")

# --- Testfall för den Nya PlanAdjuster ---

def test_pen_traversal_structure(catalog):
    """
    STEG 1 TEST: Verifierar att den grundläggande strukturen för "3D-pennan"
    i PlanAdjuster finns på plats och kan anropas utan fel.
    """
    # ARRANGE
    # Skapa en minimal semantisk plan med bara två ändpunkter och ett rör.
    nodes: List[NodeInfo] = [
        EndpointNodeInfo(id="node_0", coords=(0, 0, 0)),
        EndpointNodeInfo(id="node_1", coords=(100, 0, 0)),
    ]
    
    semantic_plan: BuildPlan = [
        {'type': 'COMPONENT', 'component_name': 'ENDPOINT', 'node_id': 'node_0', 'pipe_spec': 'SMS_25'},
        {'type': 'STRAIGHT', 'pipe_spec': 'SMS_25'},
        {'type': 'COMPONENT', 'component_name': 'ENDPOINT', 'node_id': 'node_1', 'pipe_spec': 'SMS_25'}
    ]
    
    graph = nx.Graph() # Tom graf, behövs ej för denna logik

    # ACT
    # Skapa adjustern och anropa huvudmetoden.
    # Detta kommer att misslyckas initialt eftersom metoden inte finns.
    adjuster = PlanAdjuster([semantic_plan], nodes, graph, catalog)
    explicit_plans = adjuster.create_explicit_plans()
    
    # ASSERT
    # För nu, verifiera bara att metoden returnerar en lista (även om den är tom)
    # och att den yttre listan innehåller en plan (även om den är tom).
    assert isinstance(explicit_plans, list), "Huvudmetoden ska returnera en lista av planer"
    assert len(explicit_plans) == 1, "Ska ha producerat en explicit plan för den semantiska planen"
    assert isinstance(explicit_plans[0], list), "Varje plan i listan ska också vara en lista (av primitiv)"
    # I detta första steg är det okej om listan med geometriska primitiv är tom.


def test_pen_draws_adjusted_straight_lines(catalog):
    """
    STEG 2 TEST: Verifierar att "3D-pennan" i PlanAdjuster korrekt
    beräknar längden på raka rör och producerar explicita LINE-primitiv.
    """
    # ARRANGE
    # Scenario: Ett enkelt U-format rör.
    nodes: List[NodeInfo] = [
        EndpointNodeInfo(id="node_0", coords=(0, 0, 0)),
        BendNodeInfo(id="node_1", coords=(100, 0, 0), angle=90.0),
        EndpointNodeInfo(id="node_2", coords=(100, 100, 0)),
    ]
    
    semantic_plan: BuildPlan = [
        {'type': 'COMPONENT', 'component_name': 'ENDPOINT', 'node_id': 'node_0', 'pipe_spec': 'SMS_25'},
        {'type': 'STRAIGHT', 'pipe_spec': 'SMS_25'},
        {'type': 'COMPONENT', 'component_name': 'BEND_90', 'node_id': 'node_1', 'pipe_spec': 'SMS_25'},
        {'type': 'STRAIGHT', 'pipe_spec': 'SMS_25'},
        {'type': 'COMPONENT', 'component_name': 'ENDPOINT', 'node_id': 'node_2', 'pipe_spec': 'SMS_25'}
    ]
    
    graph = nx.Graph()

    # ACT
    adjuster = PlanAdjuster([semantic_plan], nodes, graph, catalog)
    explicit_plans = adjuster.create_explicit_plans()
    explicit_plan = explicit_plans[0]

    # ASSERT
    # I denna enkla implementation finns bara en linje per segment.
    assert len(explicit_plan) == 2, "Planen ska innehålla exakt två linjer för tre noder"
    
    line1 = explicit_plan[0]
    line2 = explicit_plan[1]

    assert line1['type'] == 'LINE'
    assert line2['type'] == 'LINE'

    # Verifiera koordinaterna för den första linjen
    # Enligt nuvarande enkel implementation dras linjen hela vägen till nodens mittpunkt.
    # Linjen ska starta vid (0,0,0) och sluta vid (100,0,0).
    assert line1['start'] == pytest.approx([0.0, 0.0, 0.0])
    assert line1['end'] == pytest.approx([100.0, 0.0, 0.0])

    # Verifiera koordinaterna för den andra linjen
    # Linjen ska börja vid (100,0,0) och gå till slutpunkten (100,100,0).
    assert line2['start'] == pytest.approx([100.0, 0.0, 0.0])
    assert line2['end'] == pytest.approx([100.0, 100.0, 0.0])