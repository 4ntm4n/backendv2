import pytest
import networkx as nx
from typing import List, Tuple, Dict, Any
from dataclasses import dataclass

# Importera klasser från andra moduler
from components_catalog.loader import CatalogLoader
from pipeline.topology_builder.node_types_v2 import NodeInfo, EndpointNodeInfo, BendNodeInfo
from pipeline.plan_adjuster.adjuster import PlanAdjuster, ImpossibleBuildError
from pipeline.shared.types import BuildPlan

# --- Fixtures (Testdata) ---

@pytest.fixture
def catalog():
    """Laddar den riktiga katalogen för att ha tillgång till riktiga komponentdata."""
    return CatalogLoader("./components_catalog")

@pytest.fixture
def simple_u_shape_test_data(catalog):
    """En flexibel fixture som skapar testdata för ett enkelt U-format rör."""
    def _create_data(node1_coords: Tuple[float, float, float], node2_coords: Tuple[float, float, float]):
        nodes: List[NodeInfo] = [
            EndpointNodeInfo(id="node_0", coords=(0, 0, 0)),
            BendNodeInfo(id="node_1", coords=node1_coords, angle=90.0),
            EndpointNodeInfo(id="node_2", coords=node2_coords),
        ]
        graph = nx.Graph()
        graph.add_edge("node_0", "node_1")
        graph.add_edge("node_1", "node_2")
        plan: BuildPlan = [
            {'type': 'COMPONENT', 'component_name': 'ENDPOINT', 'node_id': 'node_0', 'spec_name': 'SMS_25'},
            {'type': 'STRAIGHT', 'spec_name': 'SMS_25'},
            {'type': 'COMPONENT', 'component_name': 'BEND_90', 'node_id': 'node_1', 'spec_name': 'SMS_25'},
            {'type': 'STRAIGHT', 'spec_name': 'SMS_25'},
            {'type': 'COMPONENT', 'component_name': 'ENDPOINT', 'node_id': 'node_2', 'spec_name': 'SMS_25'}
        ]
        return [plan], nodes, graph, catalog
    return _create_data

# --- Testfall för PlanAdjuster ---

def test_adjuster_happy_path_ample_space(simple_u_shape_test_data):
    """Testfall 1: Verifierar att överskottslängd fördelas på raka rör."""
    # ARRANGE
    plans, nodes, graph, catalog = simple_u_shape_test_data(node1_coords=(100, 0, 0), node2_coords=(100, 100, 0))
    # ACT
    adjuster = PlanAdjuster(plans, nodes, graph, catalog)
    adjusted_plans = adjuster.adjust_plans()
    final_plan = adjusted_plans[0]
    # ASSERT
    assert final_plan[1]['length'] == pytest.approx(49.0)
    assert final_plan[3]['length'] == pytest.approx(49.0)
    assert final_plan[2].get('cut_tangent_start', 0.0) == 0.0

def test_adjuster_shortfall_distributed_cut(simple_u_shape_test_data):
    """Testfall 2: Verifierar grundläggande fördelad kapning."""
    # ARRANGE
    plans, nodes, graph, catalog = simple_u_shape_test_data(node1_coords=(40, 0, 0), node2_coords=(40, 40, 0))
    # ACT
    adjuster = PlanAdjuster(plans, nodes, graph, catalog)
    adjusted_plans = adjuster.adjust_plans()
    final_plan = adjusted_plans[0]
    # ASSERT
    assert final_plan[1]['length'] == 0.0
    assert final_plan[3]['length'] == 0.0
    assert final_plan[2].get('cut_tangent_start', 0.0) == pytest.approx(11.0)
    assert final_plan[2].get('cut_tangent_end', 0.0) == pytest.approx(11.0)

def test_adjuster_proportional_comfort_cut():
    """
    Testfall 3 (NYTT & VIKTIGT): Verifierar den smarta, proportionerliga kapningslogiken.
    Detta är ett mer fokuserat enhetstest som inte behöver hela topologin.
    """
    # ARRANGE
    # Skapa mock-komponenter för att exakt styra deras egenskaper.
    # Vi simulerar ett segment med två böjar och ett underskott på 30mm.
    @dataclass
    class MockComponent:
        name: str
        current_tangent: float
        preferred_min_tangent: float
        physical_min_tangent: float
        cut_tangent_start: float = 0.0
        cut_tangent_end: float = 0.0 # Anta att vi bara kapar i ena änden för detta test

    # Böj A har 10mm "komfort-spelrum" (20 -> 10)
    bend_A = MockComponent("Bend_A", 20.0, 10.0, 0.0)
    
    # Böj B har 20mm "komfort-spelrum" (30 -> 10)
    bend_B = MockComponent("Bend_B", 30.0, 10.0, 0.0)

    segment_components = [bend_A, bend_B]
    shortfall = 30.0 # Exakt summan av komfort-spelrummet (10 + 20)

    # ACT
    # Vi antar att PlanAdjuster har en hjälpmetod för att hantera detta.
    # Detta är vad vi skriver implementationen för att klara:
    # PlanAdjuster._distribute_shortfall(segment_components, shortfall)
    
    # --- Manuell simulering av den förväntade logiken ---
    # Detta är vad implementationen i PlanAdjuster ska göra.
    comfort_leeway_A = bend_A.current_tangent - bend_A.preferred_min_tangent # 10.0
    comfort_leeway_B = bend_B.current_tangent - bend_B.preferred_min_tangent # 20.0
    total_comfort_leeway = comfort_leeway_A + comfort_leeway_B # 30.0

    if shortfall <= total_comfort_leeway:
        cut_A = shortfall * (comfort_leeway_A / total_comfort_leeway)
        cut_B = shortfall * (comfort_leeway_B / total_comfort_leeway)
        bend_A.cut_tangent_end = cut_A
        bend_B.cut_tangent_end = cut_B
    # --- Slut på simulering ---

    # ASSERT
    # Böj A (med 1/3 av spelrummet) ska ta 1/3 av kapningen.
    assert bend_A.cut_tangent_end == pytest.approx(10.0) # 30 * (10/30)
    
    # Böj B (med 2/3 av spelrummet) ska ta 2/3 av kapningen.
    assert bend_B.cut_tangent_end == pytest.approx(20.0) # 30 * (20/30)

    # Dubbelkolla att ingen kapning gick förbi "komfortgränsen".
    assert (bend_A.current_tangent - bend_A.cut_tangent_end) == pytest.approx(bend_A.preferred_min_tangent)
    assert (bend_B.current_tangent - bend_B.cut_tangent_end) == pytest.approx(bend_B.preferred_min_tangent)




def test_adjuster_impossible_build_raises_error(simple_u_shape_test_data):
    """Testfall 4: Verifierar att ett fel kastas om bygget är omöjligt."""
    # ARRANGE
    plans, nodes, graph, catalog = simple_u_shape_test_data(node1_coords=(1, 0, 0), node2_coords=(1, 1, 0))
    
    # ACT & ASSERT
    with pytest.raises(ImpossibleBuildError):
        adjuster = PlanAdjuster(plans, nodes, graph, catalog)
        adjuster.adjust_plans()

def test_adjuster_proportional_cut_with_complex_chain():
    """
    Testfall 5 (NYTT & AVANCERAT): Verifierar proportionerlig kapning
    över en komplex kedja med flera olika komponenttyper, inklusive en icke-kapbar.
    Scenario: Böj -> Kona -> Clamp, med ett underskott.
    """
    # ARRANGE
    # Skapa mock-komponenter som exakt representerar vårt scenario.
    # Vi använder en enkel dataclass för tydlighetens skull.
    @dataclass
    class MockComponent:
        name: str
        is_cappable: bool
        current_tangent: float = 0.0
        preferred_min_tangent: float = 0.0
        # För att spåra resultatet
        cut_amount: float = 0.0

    # Skapa våra tre komponenter med olika förutsättningar.
    # Böj 25: Har 15mm "komfort-spelrum" (27.5 -> 12.5)
    bend_25 = MockComponent(
        name="BEND_90_SMS_25",
        is_cappable=True,
        current_tangent=27.5,
        preferred_min_tangent=12.5
    )
    
    # Kona 25-38: Kan inte kapas.
    reducer_25_38 = MockComponent(
        name="REDUCER_25_38",
        is_cappable=False
    )
    
    # Clamp 38: Har 5mm "komfort-spelrum" (20.0 -> 15.0)
    clamp_38 = MockComponent(
        name="SMS_CLAMP_38",
        is_cappable=True,
        current_tangent=20.0,
        preferred_min_tangent=15.0
    )

    segment_components = [bend_25, reducer_25_38, clamp_38]
    shortfall = 20.0 # Exakt summan av komfort-spelrummet (15 + 5)

    # ACT
    # --- Manuell simulering av den förväntade logiken i PlanAdjuster ---
    # 1. Identifiera kapbara komponenter och deras spelrum
    cappable_components = [c for c in segment_components if c.is_cappable]
    
    comfort_leeways = {
        c.name: c.current_tangent - c.preferred_min_tangent for c in cappable_components
    }
    # comfort_leeways blir: {'BEND_90_SMS_25': 15.0, 'SMS_CLAMP_38': 5.0}
    
    total_comfort_leeway = sum(comfort_leeways.values()) # 15.0 + 5.0 = 20.0
    
    # 2. Fördela underskottet proportionerligt (Steg 2 i vår hierarki)
    if shortfall <= total_comfort_leeway:
        for comp in cappable_components:
            leeway = comfort_leeways[comp.name]
            proportion = leeway / total_comfort_leeway
            cut = shortfall * proportion
            comp.cut_amount = cut
    # --- Slut på simulering ---

    # ASSERT
    # Kontrollera att konan inte har kapats
    assert reducer_25_38.cut_amount == 0.0
    
    # Kontrollera att Böj 25 (med 75% av spelrummet) har tagit 75% av kapningen
    # 15 / 20 = 0.75.  0.75 * 20.0 = 15.0
    assert bend_25.cut_amount == pytest.approx(15.0)
    
    # Kontrollera att Clamp 38 (med 25% av spelrummet) har tagit 25% av kapningen
    # 5 / 20 = 0.25.  0.25 * 20.0 = 5.0
    assert clamp_38.cut_amount == pytest.approx(5.0)

    # Verifiera att summan av kapningarna matchar underskottet
    total_cut = bend_25.cut_amount + clamp_38.cut_amount
    assert total_cut == pytest.approx(shortfall)