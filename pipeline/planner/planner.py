
#detta är pipeline/planner/planner.py
from typing import Dict, Any, List, Tuple, Optional
import networkx as nx

from components_catalog.loader import CatalogLoader
from pipeline.topology_builder.node_types_v2 import NodeInfo, EndpointNodeInfo, BendNodeInfo, TeeNodeInfo
from pipeline.shared.types import BuildPlanItem


class Planner:
    """
    Översätter en berikad topologi-graf till en lista av sekventiella byggplaner.
    """
    def __init__(self, nodes: List[NodeInfo], topology: nx.Graph, catalog: CatalogLoader):
        self.nodes = nodes
        self.nodes_by_id = {node.id: node for node in nodes}
        self.topology = topology
        self.catalog = catalog
        self.visited_edges = set()

    def create_plans(self) -> List[List[Dict[str, Any]]]: # Returtypen är nu mer generell
        """
        Huvudmetod som hittar alla startpunkter och genererar en resplan för varje gren.
        """
        print("--- Modul 3 (Planner): Startar ---")
        all_plans: List[List[Dict[str, Any]]] = []

        start_nodes = [node for node in self.nodes if isinstance(node, EndpointNodeInfo)]

        for start_node in start_nodes:
            if self.topology.degree(start_node.id) > 0:
                neighbor_id = list(self.topology.neighbors(start_node.id))[0]
                edge_tuple = tuple(sorted((start_node.id, neighbor_id)))
                if edge_tuple in self.visited_edges:
                    continue

            plan = self._traverse_and_build_plan(start_node)
            if plan:
                all_plans.append(plan)

        # Uppdaterat print-meddelande
        print(f"--- Planner: Klar. {len(all_plans)} resplan(er) skapade. ---")
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

    def _traverse_and_build_plan(self, start_node: NodeInfo) -> List[Dict[str, Any]]:
        """
        Implementerar "vandringen" för att bygga en enskild, linjär och
        konceptuell resplan som bara består av nod- och kant-ID:n.
        """
        print(f"   -> Bygger resplan som startar från nod {start_node.id[:8]}...")

        plan: List[Dict[str, Any]] = []
        current_node = start_node
        previous_node_id = None

        while current_node:
            # Lägg bara till nodens ID
            plan.append({'type': 'NODE', 'id': current_node.id})

            next_node_id = self._find_next_node(current_node, previous_node_id)

            if next_node_id:
                edge_tuple = tuple(sorted((current_node.id, next_node_id)))
                self.visited_edges.add(edge_tuple)

                # --- START PÅ ÄNDRING ---
                # Hämta kantens data (inklusive längd) från topologi-grafen.
                edge_data = self.topology.edges[edge_tuple]
                edge_length = edge_data.get('length') # Använd .get() för säkerhets skull

                # Skapa ett berikat kant-objekt som inkluderar längden.
                plan.append({
                    'type': 'EDGE',
                    'id': edge_tuple,
                    'length': edge_length
                })
                # --- SLUT PÅ ÄNDRING ---

                previous_node_id = current_node.id
                current_node = self.nodes_by_id.get(next_node_id)
            else:
                current_node = None

        return plan

    def _create_straight_item(self, edge_data: Dict) -> BuildPlanItem:
        """Skapar ett BuildPlanItem för ett rakt rör."""
        return {
            'type': 'STRAIGHT',
            'pipe_spec': edge_data.get('pipe_spec'),
            'is_construction': edge_data.get('is_construction'),
            'length': None
        }
