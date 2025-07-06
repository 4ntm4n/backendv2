from typing import Dict, Any, List, Tuple, Optional
import networkx as nx

from components_catalog.loader import CatalogLoader
from pipeline.topology_builder.node_types_v2 import NodeInfo, EndpointNodeInfo, BendNodeInfo, TeeNodeInfo
from pipeline.shared.types import BuildPlanItem

class BuildPlanner:
    """
    Översätter en berikad topologi-graf till en lista av sekventiella byggplaner.
    """
    def __init__(self, nodes: List[NodeInfo], topology: nx.Graph, catalog: CatalogLoader):
        self.nodes = nodes
        self.nodes_by_id = {node.id: node for node in nodes}
        self.topology = topology
        self.catalog = catalog
        self.visited_edges = set()

    def create_plans(self) -> List[List[BuildPlanItem]]:
        """
        Huvudmetod som hittar alla startpunkter och genererar en byggplan för varje gren.
        """
        print("--- Modul 3 (Build Planner): Startar ---")
        all_plans: List[List[BuildPlanItem]] = []
        
        start_nodes = [node for node in self.nodes if isinstance(node, EndpointNodeInfo)]
        
        for start_node in start_nodes:
            # Kontrollera om den första kanten från denna startpunkt redan har planerats
            if self.topology.degree(start_node.id) > 0:
                neighbor_id = list(self.topology.neighbors(start_node.id))[0]
                edge_tuple = tuple(sorted((start_node.id, neighbor_id)))
                if edge_tuple in self.visited_edges:
                    continue
            
            plan = self._traverse_and_build_plan(start_node)
            if plan:
                all_plans.append(plan)

        print(f"--- Build Planner: Klar. {len(all_plans)} byggplan(er) skapade. ---")
        return all_plans

    def _traverse_and_build_plan(self, start_node: NodeInfo) -> List[BuildPlanItem]:
        """
        Implementerar "vandringen" för att bygga en enskild, linjär byggplan.
        Stannar när den når en redan besökt kant.
        """
        print(f"  -> Bygger plan som startar från nod {start_node.id[:8]}...")
        
        plan: List[BuildPlanItem] = []
        current_node = start_node
        previous_node_id = None

        while current_node:
            if component_item := self._create_component_item(current_node):
                plan.append(component_item)

            # ### NY, SMARTARE LOGIK FÖR ATT HITTA NÄSTA STEG ###
            next_node_id = None
            for neighbor in self.topology.neighbors(current_node.id):
                # Ignorera noden vi precis kom ifrån
                if neighbor == previous_node_id:
                    continue
                
                # Kontrollera om kanten till denna granne redan har besökts
                edge_tuple = tuple(sorted((current_node.id, neighbor)))
                if edge_tuple not in self.visited_edges:
                    next_node_id = neighbor
                    break # Vi har hittat vår nästa, obesökta väg

            if next_node_id:
                edge_tuple = tuple(sorted((current_node.id, next_node_id)))
                self.visited_edges.add(edge_tuple)

                edge_data = self.topology.edges[edge_tuple]
                plan.append(self._create_straight_item(edge_data))
                
                previous_node_id = current_node.id
                current_node = self.nodes_by_id.get(next_node_id)
            else:
                # Ingen obesökt väg framåt, denna gren är klar.
                current_node = None
        
        return plan

    def _create_component_item(self, node: NodeInfo) -> Optional[BuildPlanItem]:
        """Skapar ett BuildPlanItem för en komponent-nod."""
        spec_name = getattr(getattr(node, 'assigned_spec', None), 'name', 'UNKNOWN_SPEC')
        
        component_type_name = node.node_type
        if isinstance(node, BendNodeInfo):
            angle = int(round(node.angle)) if node.angle is not None else 0
            if angle == 90: component_type_name = "BEND_90"
            elif angle == 45: component_type_name = "BEND_45"
            else: component_type_name = "BEND_CUSTOM"
        elif isinstance(node, EndpointNodeInfo):
            component_type_name = getattr(node, 'fitting_type', 'OPEN')
        
        # För testets skull skapar vi en komponent även för OPEN
        length = 0.0 if component_type_name == "OPEN" else 50.0

        return {
            'type': 'COMPONENT',
            'component_name': f"{component_type_name}_{spec_name}",
            'node_id': node.id,
            'spec_name': spec_name,
            'length': length
        }

    def _create_straight_item(self, edge_data: Dict) -> BuildPlanItem:
        """Skapar ett BuildPlanItem för ett rakt rör."""
        return {
            'type': 'STRAIGHT',
            'spec_name': edge_data.get('spec_name'),
            'is_construction': edge_data.get('is_construction'),
            'length': None
        }
