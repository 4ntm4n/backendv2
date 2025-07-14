# tests/centerline_builder/test_builder.py

import sys
import os
import pytest
from unittest.mock import MagicMock
import networkx as nx

# Lägg till projektets rotmapp i sökvägen för att lösa importer
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

# Importera klassen vi vill testa och de datatyper den behöver
from pipeline.planner.planner import Planner
from pipeline.topology_builder.node_types_v2 import EndpointNodeInfo, BendNodeInfo


def test_planner_simple_linear_plan():
    """
    Testar att BuildPlanner kan skapa en korrekt, linjär byggplan från
    en enkel topologi (Ändpunkt -> Böj -> Ändpunkt).
    """
    # --- Steg 1: ARRANGE ---
    # Skapa den indata som vår planner förväntar sig från TopologyBuilder.

    # 1a: Skapa en lista med "låtsas"-noder
    start_node = EndpointNodeInfo(coords=(0, 0, 0))
    bend_node = BendNodeInfo(coords=(100, 0, 0), angle=90.0)
    end_node = EndpointNodeInfo(coords=(100, 100, 0))
    nodes = [start_node, bend_node, end_node]

    # 1b: Skapa en "låtsas"-topologi (networkx-graf)
    topology = nx.Graph()
    # Lägg till kanter och berika dem med den data som TopologyBuilder skulle ha gjort
    topology.add_edge(start_node.id, bend_node.id, spec_name="SMS_25", is_construction=False)
    topology.add_edge(bend_node.id, end_node.id, spec_name="SMS_25", is_construction=False)

    # 1c: Skapa en mock för vår CatalogLoader
    mock_catalog = MagicMock()

    # --- Steg 2: ACT ---
    # Skapa en instans av vår planner och kör huvudmetoden.
    planner = Planner(nodes=nodes, topology=topology, catalog=mock_catalog)
    list_of_plans = planner.create_plans()

    # --- Steg 3: ASSERT ---
    # Verifiera att resultatet är korrekt.

    # 3a: Kontrollera den övergripande strukturen
    assert list_of_plans is not None, "Resultatet ska inte vara None"
    assert len(list_of_plans) == 1, "Ska ha skapat exakt en byggplan för denna enkla topologi"
    
    single_plan = list_of_plans[0]
    # Planen ska vara: Endpoint -> Straight -> Bend -> Straight -> Endpoint
    assert len(single_plan) == 5, f"Planen ska ha 5 steg, men hade {len(single_plan)}"

    # 3b: Kontrollera sekvensen och typerna
    expected_sequence = ['COMPONENT', 'STRAIGHT', 'COMPONENT', 'STRAIGHT', 'COMPONENT']
    actual_sequence = [item['type'] for item in single_plan]
    assert actual_sequence == expected_sequence, "Sekvensen av typer i byggplanen är felaktig"

    # 3c: Kontrollera specifik data
    assert single_plan[0]['node_id'] == start_node.id, "Första komponenten ska vara startnoden"
    assert single_plan[1]['spec_name'] == "SMS_25", "Första raka röret ska ha rätt specifikation"
    assert single_plan[2]['node_id'] == bend_node.id, "Tredje komponenten ska vara böj-noden"
    assert single_plan[4]['node_id'] == end_node.id, "Sista komponenten ska vara slutnoden"

    print("\nTest av BuildPlanner lyckades!")

