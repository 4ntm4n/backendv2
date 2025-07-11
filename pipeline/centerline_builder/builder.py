from typing import Dict, Any, List, Tuple, Optional
import networkx as nx

from components_catalog.loader import CatalogLoader
from pipeline.topology_builder.node_types_v2 import NodeInfo, EndpointNodeInfo, BendNodeInfo, TeeNodeInfo
from pipeline.shared.types import BuildPlanItem

class CenterlineBuilder:
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
        print("--- Modul 3 (Centerline Builder): Startar ---")
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

        print(f"--- Centerline Builder: Klar. {len(all_plans)} byggplan(er) skapade. ---")
        return all_plans

    def _find_next_node(self, current_node: NodeInfo, previous_node_id: Optional[str]) -> Optional[str]:
        """
        En smartare hjälpmetod för att avgöra vilken nod som ska besökas härnäst.
        Prioriterar den raka vägen ("the run") vid T-korsningar.
        """
        # Hämta alla möjliga vägar framåt (alla grannar utom den vi kom ifrån)
        potential_paths = [n_id for n_id in self.topology.neighbors(current_node.id) if n_id != previous_node_id]

        # Filtrera bort vägar (kanter) som redan har besökts
        unvisited_paths = []
        for neighbor_id in potential_paths:
            edge_tuple = tuple(sorted((current_node.id, neighbor_id)))
            if edge_tuple not in self.visited_edges:
                unvisited_paths.append(neighbor_id)
        
        if not unvisited_paths:
            return None

        # Om det är ett T-rör, försök hitta den fortsatta "run"-noden
        if isinstance(current_node, TeeNodeInfo):
            # Leta efter en nod i unvisited_paths som också finns i run_node_ids
            for node_id in unvisited_paths:
                if node_id in current_node.run_node_ids:
                    # Vi har hittat den raka vägen framåt!
                    return node_id
        
        # Om det inte är ett T-rör, eller om "run"-vägen redan var besökt,
        # ta bara den första bästa tillgängliga obesökta vägen.
        return unvisited_paths[0]

    def _traverse_and_build_plan(self, start_node: NodeInfo) -> List[BuildPlanItem]:
        """
        Implementerar "vandringen" för att bygga en enskild, linjär byggplan.
        Använder nu den smartare _find_next_node-metoden.
        """
        print(f"  -> Bygger plan som startar från nod {start_node.id[:8]}...")
        
        plan: List[BuildPlanItem] = []
        current_node = start_node
        previous_node_id = None

        while current_node:
            if component_item := self._create_component_item(current_node):
                plan.append(component_item)

            # ### ERSÄTT DEN GAMLA LOGIKEN MED ETT ANROP TILL DEN NYA HJÄLPMETODEN ###
            next_node_id = self._find_next_node(current_node, previous_node_id)

            if next_node_id:
                edge_tuple = tuple(sorted((current_node.id, next_node_id)))
                self.visited_edges.add(edge_tuple)

                edge_data = self.topology.edges[edge_tuple]
                plan.append(self._create_straight_item(edge_data))
                
                previous_node_id = current_node.id
                current_node = self.nodes_by_id.get(next_node_id)
            else:
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
