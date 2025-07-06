# tests/topology_builder/test_builder.py

import sys
import os
import pytest
from unittest.mock import MagicMock
import networkx as nx
import math

# --- KORRIGERING FÖR IMPORT-FEL ---
# Denna kod lägger till projektets rotmapp i Pythons sökväg.
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)
# ------------------------------------

# Importera klassen vi vill testa med en giltig sökväg
from pipeline.topology_builder.builder import TopologyBuilder
from pipeline.topology_builder.node_types_v2 import BendNodeInfo, TeeNodeInfo, NodeInfo, EndpointNodeInfo

def find_node_by_type(nodes: list[NodeInfo], node_type: type) -> NodeInfo | None:
    """Hjälpfunktion för att hitta en nod av en specifik typ i en lista."""
    return next((node for node in nodes if isinstance(node, node_type)), None)


def test_topology_builder_simple_bend_scenario():
    """
    Testar TopologyBuilder med ett realistiskt scenario som inkluderar
    "snapping" av vinklar till närmsta isometriska axel.
    """
    # --- Steg 1: ARRANGE ---
    parsed_sketch_data = {
        "segments": [
            {
                "id": "line_1",
                "start_point": (10.0, 10.0),
                "end_point": (10.0, 110.0), # Vinkel 90 grader -> snappar till -Z
                "spec_name": "SMS_25",
                "length_dimension": 100.0,
                "is_construction": False
            },
            {
                "id": "line_2",
                "start_point": (10.0, 110.0),
                "end_point": (96.6, 160.0), # Vinkel 30 grader -> snappar till +X
                "spec_name": "SMS_25",
                "length_dimension": 100.0,
                "is_construction": False
            }
        ],
        "origin": None
    }
    mock_catalog = MagicMock()
    mock_catalog.get_spec.return_value = MagicMock(name="MockSpec")

    # --- Steg 2: ACT ---
    builder = TopologyBuilder(parsed_sketch=parsed_sketch_data, catalog=mock_catalog)
    nodes, topology = builder.build()

    # --- Steg 3: ASSERT ---
    assert len(nodes) == 3, "Ska ha skapat 3 unika noder"
    
    bend_node = find_node_by_type(nodes, BendNodeInfo)
    assert bend_node is not None, "En BendNodeInfo borde ha skapats"
    # Vinkeln mellan -Z och +X är 90 grader.
    assert pytest.approx(bend_node.angle) == 90.0, "Vinkeln för böjen ska vara 90 grader"

    print("\nTest av 'simple_bend_scenario' lyckades!")


### KORRIGERAT TESTFALL FÖR T-RÖR ###
def test_topology_builder_tee_junction_enrichment():
    """
    Testar att _enrich_nodes korrekt identifierar ett T-rör och
    korrekt tilldelar dess 'run_node_ids' och 'branch_node_id'.
    """
    # --- Steg 1: ARRANGE ---
    # Skapa en geometriskt korrekt T-korsning.
    # Huvudloppet går längs X-axeln. Avsticket går längs Y-axeln.
    parsed_sketch_data = {
        "segments": [
            # Linje 1: Start -> Tee. Vinkel 30 grader -> snappar till +X
            {"id": "line_1", "start_point": (0,0), "end_point": (86.6, 50.0), "length_dimension": 100.0, "spec_name": "SMS_38", "is_construction": False},
            # Linje 2: Tee -> Main End. Vinkel 30 grader -> snappar till +X (fortsättning av huvudloppet)
            {"id": "line_2", "start_point": (86.6, 50.0), "end_point": (173.2, 100.0), "length_dimension": 100.0, "spec_name": "SMS_38", "is_construction": False},
            # Linje 3: Tee -> Branch End. Vinkel 330 grader -> snappar till +Y
            {"id": "line_3", "start_point": (86.6, 50.0), "end_point": (173.2, 0.0), "length_dimension": 100.0, "spec_name": "SMS_25", "is_construction": False},
        ]
    }
    mock_catalog = MagicMock()
    mock_catalog.get_spec.return_value = MagicMock(name="MockSpec")

    # --- Steg 2: ACT ---
    builder = TopologyBuilder(parsed_sketch=parsed_sketch_data, catalog=mock_catalog)
    nodes, topology = builder.build()

    # --- Steg 3: ASSERT ---
    assert len(nodes) == 4, "Ska ha skapat 4 unika noder"

    tee_node = find_node_by_type(nodes, TeeNodeInfo)
    assert tee_node is not None, "En TeeNodeInfo borde ha skapats"
    
    # Hitta de andra noderna baserat på deras förväntade 3D-koordinater
    start_node = next((n for n in nodes if n.coords == (0.0, 0.0, 0.0)), None)
    main_end_node = next((n for n in nodes if n.coords == (200.0, 0.0, 0.0)), None)
    branch_end_node = next((n for n in nodes if n.coords == (100.0, 100.0, 0.0)), None)

    assert all([start_node, main_end_node, branch_end_node]), "Kunde inte hitta alla förväntade noder vid deras 3D-koordinater"

    # Verifiera att run/branch har identifierats korrekt
    assert hasattr(tee_node, 'run_node_ids'), "TeeNode saknar 'run_node_ids'"
    assert hasattr(tee_node, 'branch_node_id'), "TeeNode saknar 'branch_node_id'"
    assert len(tee_node.run_node_ids) == 2
    assert start_node.id in tee_node.run_node_ids
    assert main_end_node.id in tee_node.run_node_ids
    assert tee_node.branch_node_id == branch_end_node.id

    print("\nTest av 'tee_junction_enrichment' lyckades!")
