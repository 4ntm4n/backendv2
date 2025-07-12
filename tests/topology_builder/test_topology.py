# tests/topology_builder/test_builder.py
import sys
import os
import pytest
from unittest.mock import MagicMock
import networkx as nx
from decimal import Decimal

# Lägg till projektets rotmapp i Pythons sökväg
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

# Importera de klasser som testas
from pipeline.topology_builder.builder import TopologyBuilder
from pipeline.topology_builder.node_types_v2 import BendNodeInfo, TeeNodeInfo, NodeInfo

# --- HJÄLPFUNKTION (Standardiserad till att alltid returnera en lista) ---

def find_nodes_by_type(nodes: list[NodeInfo], node_type: type) -> list[NodeInfo]:
    """Hjälpfunktion för att hitta ALLA noder av en specifik typ i en lista."""
    return [node for node in nodes if isinstance(node, node_type)]

# --- BEFINTLIGA TESTER (Uppdaterade för att använda den nya hjälpfunktionen) ---

def test_topology_builder_simple_bend_scenario():
    """
    Testar en enkel 90-graders böj.
    """
    # ARRANGE
    parsed_sketch_data = {
        "segments": [
            {
                "id": "line_1", "start_point": {"x": 0.0, "y": 0.0}, "end_point": {"x": 86.6, "y": 50.0},
                "length_dimension": 100.0, "spec_name": "SMS_25", "is_construction": False
            },
            {
                "id": "line_2", "start_point": {"x": 86.6, "y": 50.0}, "end_point": {"x": 86.6, "y": 150.0},
                "length_dimension": 100.0, "spec_name": "SMS_25", "is_construction": False
            }
        ],
    }
    mock_catalog = MagicMock()

    # ACT
    builder = TopologyBuilder(parsed_sketch=parsed_sketch_data, catalog=mock_catalog)
    nodes, topology = builder.build()

    # ASSERT
    assert len(nodes) == 3, "Ska ha skapat 3 unika noder"
    
    # UPPDATERAD LOGIK: Hantera listan som returneras
    bend_nodes = find_nodes_by_type(nodes, BendNodeInfo)
    assert len(bend_nodes) == 1, "Exakt en BendNodeInfo borde ha skapats"
    bend_node = bend_nodes[0] # Hämta ut det enda objektet från listan
    
    assert pytest.approx(bend_node.angle) == 90.0
    
    bend_node_actual = next((n for n in nodes if n.coords == pytest.approx((100.0, 0.0, 0.0))), None)
    assert bend_node_actual is not None, "Böj-noden har fel 3D-koordinater"


def test_topology_builder_tee_junction_enrichment():
    """
    Testar ett T-rör för att säkerställa att run och branch identifieras korrekt.
    """
    # ARRANGE
    parsed_sketch_data = {
        "segments": [
            {"id": "line_1", "start_point": {"x": 0.0, "y": 0.0}, "end_point": {"x": 86.6, "y": 50.0}, "length_dimension": 100.0, "spec_name": "SMS_38", "is_construction": False},
            {"id": "line_2", "start_point": {"x": 86.6, "y": 50.0}, "end_point": {"x": 173.2, "y": 100.0}, "length_dimension": 100.0, "spec_name": "SMS_38", "is_construction": False},
            {"id": "line_3", "start_point": {"x": 86.6, "y": 50.0}, "end_point": {"x": 173.2, "y": 0.0}, "length_dimension": 100.0, "spec_name": "SMS_25", "is_construction": False},
        ]
    }
    mock_catalog = MagicMock()

    # ACT
    builder = TopologyBuilder(parsed_sketch=parsed_sketch_data, catalog=mock_catalog)
    nodes, topology = builder.build()

    # ASSERT
    assert len(nodes) == 4
    
    # UPPDATERAD LOGIK: Hantera listan som returneras
    tee_nodes = find_nodes_by_type(nodes, TeeNodeInfo)
    assert len(tee_nodes) == 1, "Exakt en TeeNodeInfo borde ha skapats"
    tee_node = tee_nodes[0] # Hämta ut det enda objektet från listan

    assert tee_node.coords == pytest.approx((100.0, 0.0, 0.0))

# --- NYTT, FÖRBÄTTRAT TEST FÖR GENVÄGAR (Oförändrat) ---

@pytest.fixture
def shortcut_sketch_data():
    """En pytest-fixture som tillhandahåller skissdata för genvägs-scenariot."""
    return {
        "segments": [
            {
                "id": "l1", "start_point": {"x": 311.7691, "y": 580.0}, "end_point": {"x": 311.7691, "y": 300.0},
                "is_construction": False, "length_dimension": 500.0, "spec_name": "SMS-38"
            },
            {
                "id": "l2_construction", "start_point": {"x": 311.7691, "y": 300.0}, "end_point": {"x": 519.6152, "y": 180.0},
                "is_construction": True, "length_dimension": 400.0, "spec_name": "SMS-38"
            },
            {
                "id": "l3_construction", "start_point": {"x": 519.6152, "y": 180.0}, "end_point": {"x": 692.8203, "y": 280.0},
                "is_construction": True, "length_dimension": 300.0, "spec_name": "SMS-38"
            },
            {
                "id": "l4", "start_point": {"x": 692.8203, "y": 280.0}, "end_point": {"x": 1004.5895, "y": 100.0},
                "is_construction": False, "length_dimension": 500.0, "spec_name": "SMS-38"
            },
            {
                "id": "l5_shortcut", "start_point": {"x": 311.7691, "y": 300.0}, "end_point": {"x": 692.8203, "y": 280.0},
                "is_construction": False, "length_dimension": None, "spec_name": "SMS-38"
            }
        ]
    }

def test_creates_non_standard_angle_from_shortcut(shortcut_sketch_data):
    """
    Testar att en genväg resulterar i en böj med en icke-standardiserad vinkel,
    vilket bevisar att genvägen har skapats korrekt.
    """
    # ARRANGE
    mock_catalog = MagicMock()
    builder = TopologyBuilder(parsed_sketch=shortcut_sketch_data, catalog=mock_catalog)
    
    # ACT
    nodes, topology = builder.build()

    # ASSERT
    assert topology.number_of_nodes() == 4, "Fel antal noder i den slutliga grafen."
    assert topology.number_of_edges() == 3, "Fel antal kanter i den slutliga grafen."

    bend_nodes = find_nodes_by_type(nodes, BendNodeInfo)
    assert len(bend_nodes) >= 1, "Inga böjar (BendNodeInfo) hittades i den berikade nodlistan."

    has_non_standard_angle = any(not pytest.approx(b.angle) == 90.0 for b in bend_nodes)
    assert has_non_standard_angle, "Ingen böj med en specialvinkel (icke-90 grader) skapades."

    edge_ids = [data['segment_id'] for _, _, data in topology.edges(data=True)]
    assert 'l5_shortcut' in edge_ids, "Genvägens segment-ID saknas i den slutliga grafen."
