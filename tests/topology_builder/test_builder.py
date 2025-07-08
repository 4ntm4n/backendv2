# tests/topology_builder/test_builder.py

import sys
import os
import pytest
from unittest.mock import MagicMock
import networkx as nx
import math

# Lägg till projektets rotmapp i Pythons sökväg
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from pipeline.topology_builder.builder import TopologyBuilder, Vec3
from pipeline.topology_builder.node_types_v2 import BendNodeInfo, TeeNodeInfo, NodeInfo, EndpointNodeInfo

def find_node_by_type(nodes: list[NodeInfo], node_type: type) -> NodeInfo | None:
    """Hjälpfunktion för att hitta en nod av en specifik typ i en lista."""
    return next((node for node in nodes if isinstance(node, node_type)), None)

def test_topology_builder_simple_bend_scenario():
    """
    Testar en böj med den korrekta orienterings-mappningen och korrekt testdata.
    """
    # ARRANGE
    # 2D-skiss: En linje snett upp-höger (30 grader, blir -X i 3D)
    # följt av en linje rakt upp (90 grader, blir -Z i 3D).
    parsed_sketch_data = {
        "segments": [
            {
                "id": "line_1", "start_point": (0.0, 0.0), "end_point": (86.6, 50.0),
                "length_dimension": 100.0, "spec_name": "SMS_25", "is_construction": False
            },
            {
                "id": "line_2", "start_point": (86.6, 50.0), "end_point": (86.6, 150.0),
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
    
    bend_node = find_node_by_type(nodes, BendNodeInfo)
    assert bend_node is not None, "En BendNodeInfo borde ha skapats"
    
    # Vinkeln mellan -X ( -1,0,0) och -Z (0,0,-1) är 90 grader.
    assert pytest.approx(bend_node.angle) == 90.0
    
    # Verifiera de korrekta 3D-koordinaterna
    start_node = next((n for n in nodes if n.coords == (0.0, 0.0, 0.0)), None)
    bend_node_actual = next((n for n in nodes if n.coords == pytest.approx((-100.0, 0.0, 0.0))), None)
    end_node = next((n for n in nodes if n.coords == pytest.approx((-100.0, 0.0, -100.0))), None)
    assert all([start_node, bend_node_actual, end_node]), "En eller flera noder har fel 3D-koordinater"


def test_topology_builder_tee_junction_enrichment():
    """
    Testar T-rörs-logiken med den korrekta orienterings-mappningen och korrekt testdata.
    """
    # ARRANGE
    # 2D-skiss: Huvudlopp längs 30 grader (-X), avstick längs 330 grader (-Y).
    parsed_sketch_data = {
        "segments": [
            {"id": "line_1", "start_point": (0,0), "end_point": (86.6, 50.0), "length_dimension": 100.0, "spec_name": "SMS_38", "is_construction": False},
            {"id": "line_2", "start_point": (86.6, 50.0), "end_point": (173.2, 100.0), "length_dimension": 100.0, "spec_name": "SMS_38", "is_construction": False},
            {"id": "line_3", "start_point": (86.6, 50.0), "end_point": (173.2, 0.0), "length_dimension": 100.0, "spec_name": "SMS_25", "is_construction": False},
        ]
    }
    mock_catalog = MagicMock()

    # ACT
    builder = TopologyBuilder(parsed_sketch=parsed_sketch_data, catalog=mock_catalog)
    nodes, topology = builder.build()

    # ASSERT
    assert len(nodes) == 4
    tee_node = find_node_by_type(nodes, TeeNodeInfo)
    assert tee_node is not None
    
    # Hitta noder baserat på deras KORREKTA förväntade 3D-koordinater
    start_node = next((n for n in nodes if n.coords == (0.0, 0.0, 0.0)), None)
    main_end_node = next((n for n in nodes if n.coords == pytest.approx((-200.0, 0.0, 0.0))), None)
    branch_end_node = next((n for n in nodes if n.coords == pytest.approx((-100.0, -100.0, 0.0))), None)

    assert all([start_node, main_end_node, branch_end_node]), "Kunde inte hitta alla förväntade noder vid deras 3D-koordinater"
    assert tee_node.coords == pytest.approx((-100.0, 0.0, 0.0))

    # Verifiera att run/branch har identifierats korrekt
    assert len(tee_node.run_node_ids) == 2
    assert start_node.id in tee_node.run_node_ids
    assert main_end_node.id in tee_node.run_node_ids
    assert tee_node.branch_node_id == branch_end_node.id
