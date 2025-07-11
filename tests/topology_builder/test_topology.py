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
    # 2D-skiss: En linje snett upp-höger (30 grader, blir +X i 3D)
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
    bend_node_actual = next((n for n in nodes if n.coords == pytest.approx((100.0, 0.0, 0.0))), None)
    end_node = next((n for n in nodes if n.coords == pytest.approx((100.0, 0.0, -100.0))), None)
    assert all([start_node, bend_node_actual, end_node]), "En eller flera noder har fel 3D-koordinater"


def test_topology_builder_tee_junction_enrichment():
    """
    Testar T-rörs-logiken med den korrekta orienterings-mappningen och korrekt testdata.
    """
    # ARRANGE
    # 2D-skiss: Huvudlopp längs 30 grader (+X), avstick längs 330 grader (+Y).
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
    main_end_node = next((n for n in nodes if n.coords == pytest.approx((200.0, 0.0, 0.0))), None)
    branch_end_node = next((n for n in nodes if n.coords == pytest.approx((100.0, 100.0, 0.0))), None)

    assert all([start_node, main_end_node, branch_end_node]), "Kunde inte hitta alla förväntade noder vid deras 3D-koordinater"
    assert tee_node.coords == pytest.approx((100.0, 0.0, 0.0))

    # Verifiera att run/branch har identifierats korrekt
    assert len(tee_node.run_node_ids) == 2
    assert start_node.id in tee_node.run_node_ids
    assert main_end_node.id in tee_node.run_node_ids
    assert tee_node.branch_node_id == branch_end_node.id

def test_topology_builder_solves_real_construction_chain(mocker):
    """
    Testar att en "speciallinje" (utan egen dimension) skapas korrekt
    genom att använda exakt data från ett verkligt testfall.
    """
    # ARRANGE
    # Exakt data från skissen som misslyckades i det manuella testet.
    parsed_sketch_data = {
        "segments": [
            {
                "id": "l1", "start_point": (277.1281, 440.0), "end_point": (277.1281, 160.0),
                "isConstruction": False, "length_dimension": 500, "pipeSpec": "SMS-38"
            },
            {
                "id": "l2", "start_point": (277.1281, 160.0), "end_point": (415.6922, 240.0),
                "isConstruction": True, "length_dimension": 400, "pipeSpec": "SMS-38"
            },
            {
                "id": "l3", "start_point": (415.6922, 240.0), "end_point": (415.6922, 40.0),
                "isConstruction": True, "length_dimension": 400, "pipeSpec": "SMS-38"
            },
            {
                "id": "l4", "start_point": (277.1281, 160.0), "end_point": (415.6922, 40.0),
                "isConstruction": False, "length_dimension": None, "pipeSpec": "SMS-38"
            },
            {
                "id": "l5", "start_point": (415.6922, 40.0), "end_point": (658.1793, -100.0),
                "isConstruction": False, "length_dimension": 1000, "pipeSpec": "SMS-38"
            }
        ]
    }
    mock_catalog = MagicMock()
    # Mocka get_spec för att undvika fel i det senare _enrich_nodes-steget.
    mocker.patch.object(mock_catalog, 'get_spec', return_value=MagicMock())

    # ACT
    builder = TopologyBuilder(parsed_sketch=parsed_sketch_data, catalog=mock_catalog)
    nodes, topology = builder.build()

    # ASSERT
    # 1. Kontrollera att topologin är ren: inga konstruktionslinjer kvar.
    # Vi förväntar oss att l2 och l3 är borttagna.
    final_edge_ids = {data['segment_id'] for _, _, data in topology.edges(data=True)}
    assert "l2" not in final_edge_ids, "Konstruktionslinje l2 borde ha tagits bort"
    assert "l3" not in final_edge_ids, "Konstruktionslinje l3 borde ha tagits bort"

    # 2. Kontrollera att den slutgiltiga grafen har rätt form.
    # Den ska ha 4 noder och 3 kanter (l1, l4, l5).
    assert topology.number_of_nodes() == 4, "Fel antal noder i den slutgiltiga grafen"
    assert topology.number_of_edges() == 3, "Fel antal kanter i den slutgiltiga grafen"

    # 3. Verifiera att "speciallinjen" (l4) existerar mellan rätt noder.
    # Vi hittar noderna baserat på deras förväntade 2D-koordinater i den ursprungliga skissen.
    # Detta är ett robust sätt att verifiera att rätt noder kopplats samman.
    node_map_2d_to_3d_id = builder.node_map_2d_to_3d_id # Antag att vi exponerar denna för testning
    
    start_node_id = node_map_2d_to_3d_id.get((277.1281, 160.0))
    end_node_id = node_map_2d_to_3d_id.get((415.6922, 40.0))

    assert start_node_id is not None, "Kunde inte hitta 3D-noden för speciallinjens startpunkt"
    assert end_node_id is not None, "Kunde inte hitta 3D-noden för speciallinjens slutpunkt"
    
    # Det absolut viktigaste testet: finns det en kant mellan dessa två noder?
    assert topology.has_edge(start_node_id, end_node_id), "Speciallinjen (l4) har inte skapats korrekt"
    
    # Verifiera att kanten som finns är just l4 och inte en konstruktionslinje
    edge_data = topology.get_edge_data(start_node_id, end_node_id)
    assert edge_data.get('segment_id') == 'l4'
    assert not edge_data.get('is_construction')



def find_node_by_coords(nodes: list[NodeInfo], target_coords: tuple, tolerance: float = 1e-4) -> NodeInfo | None:
    """Hjälpfunktion för att hitta en nod baserat på dess 3D-koordinater."""
    for node in nodes:
        if (math.isclose(node.coords[0], target_coords[0], abs_tol=tolerance) and
            math.isclose(node.coords[1], target_coords[1], abs_tol=tolerance) and
            math.isclose(node.coords[2], target_coords[2], abs_tol=tolerance)):
            return node
    return None

def test_topology_builder_solves_real_construction_chain(mocker):
    """
    Testar att en "speciallinje" (utan egen dimension) skapas korrekt
    genom att använda exakt data från ett verkligt testfall.
    """
    # ARRANGE
    # Exakt data från skissen som misslyckades i det manuella testet.
    parsed_sketch_data = {
        "segments": [
            {
                "id": "l1", "start_point": (277.1281, 440.0), "end_point": (277.1281, 160.0),
                "isConstruction": False, "length_dimension": 500, "pipeSpec": "SMS-38"
            },
            {
                "id": "l2", "start_point": (277.1281, 160.0), "end_point": (415.6922, 240.0),
                "isConstruction": True, "length_dimension": 400, "pipeSpec": "SMS-38"
            },
            {
                "id": "l3", "start_point": (415.6922, 240.0), "end_point": (415.6922, 40.0),
                "isConstruction": True, "length_dimension": 400, "pipeSpec": "SMS-38"
            },
            {
                "id": "l4", "start_point": (277.1281, 160.0), "end_point": (415.6922, 40.0),
                "isConstruction": False, "length_dimension": None, "pipeSpec": "SMS-38"
            },
            {
                "id": "l5", "start_point": (415.6922, 40.0), "end_point": (658.1793, -100.0),
                "isConstruction": False, "length_dimension": 1000, "pipeSpec": "SMS-38"
            }
        ]
    }
    mock_catalog = MagicMock()
    # Mocka get_spec för att undvika fel i det senare _enrich_nodes-steget.
    mocker.patch.object(mock_catalog, 'get_spec', return_value=MagicMock())

    # ACT
    builder = TopologyBuilder(parsed_sketch=parsed_sketch_data, catalog=mock_catalog)
    nodes, topology = builder.build()

    # ASSERT
    # 1. Kontrollera att topologin är ren: inga konstruktionslinjer kvar.
    # Vi förväntar oss att l2 och l3 är borttagna.
    final_edge_ids = {data.get('segment_id') for _, _, data in topology.edges(data=True)}
    assert "l2" not in final_edge_ids, "Konstruktionslinje l2 borde ha tagits bort"
    assert "l3" not in final_edge_ids, "Konstruktionslinje l3 borde ha tagits bort"

    # 2. Kontrollera att den slutgiltiga grafen har rätt form.
    # Den ska ha 4 noder och 3 kanter (l1, l4, l5).
    assert topology.number_of_nodes() == 4, f"Förväntade 4 noder, men fick {topology.number_of_nodes()}"
    assert topology.number_of_edges() == 3, f"Förväntade 3 kanter, men fick {topology.number_of_edges()}"

    # 3. Verifiera att "speciallinjen" (l4) existerar mellan rätt noder.
    # Vi hittar noderna baserat på deras förväntade 3D-koordinater.
    # Beräkning: start vid (0,0,0). l1 (500mm @ 270deg) -> (0,0,500).
    # l2 (400mm @ 330deg) -> (0,400,500). l3 (400mm @ 270deg) -> (0,400,900).
    # l5 (1000mm @ 30deg) -> (1000,400,900).
    
    # Hitta noderna via deras beräknade 3D-positioner
    node_l1_end = find_node_by_coords(nodes, (0.0, 0.0, 500.0))
    node_l4_end = find_node_by_coords(nodes, (0.0, 400.0, 900.0)) # Detta är slutpunkten för speciallinjen

    assert node_l1_end is not None, "Kunde inte hitta 3D-noden för speciallinjens startpunkt"
    assert node_l4_end is not None, "Kunde inte hitta 3D-noden för speciallinjens slutpunkt"
    
    # Det absolut viktigaste testet: finns det en kant mellan dessa två noder?
    assert topology.has_edge(node_l1_end.id, node_l4_end.id), "Speciallinjen (l4) har inte skapats korrekt"
    
    # Verifiera att kanten som finns är just l4 och inte en konstruktionslinje
    edge_data = topology.get_edge_data(node_l1_end.id, node_l4_end.id)
    assert edge_data.get('segment_id') == 'l4'
    assert not edge_data.get('is_construction')