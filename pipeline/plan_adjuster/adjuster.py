import math
from typing import Dict, Any, List

# Importera endast det vi faktiskt behöver för detta steg
from components_catalog.loader import CatalogLoader
from pipeline.topology_builder.node_types_v2 import NodeInfo
from pipeline.shared.types import BuildPlan

class ImpossibleBuildError(Exception):
    """Ett anpassat fel som kastas när en design är geometriskt omöjlig."""
    pass

class PlanAdjuster:
    """
    MODUL 4: Geometri-Ingenjören.
    Ansvar: Att omvandla en semantisk byggplan till en geometriskt
    explicit ritning som är redo att skickas till den "dumma" executorn.
    """
    def __init__(self, semantic_plans: List[BuildPlan], nodes: List[NodeInfo], topology: Any, catalog: CatalogLoader):
        self.semantic_plans = semantic_plans
        self.nodes_by_id = {node.id: node for node in nodes}
        self.topology = topology
        self.catalog = catalog

    def create_explicit_plans(self) -> List[List[Dict[str, Any]]]:
        """
        Huvudmetod som producerar en lista av explicita geometriska planer.
        """
        print("--- Modul 4 (PlanAdjuster): Skapar explicit geometrisk plan ---")
        explicit_plans = []
        for plan in self.semantic_plans:
            # Anropar den privata hjälpmetoden för varje plan
            explicit_plan = self._create_explicit_plan_from_semantic(plan)
            explicit_plans.append(explicit_plan)
            
        print("--- PlanAdjuster: Klar. ---")
        return explicit_plans

    def _create_explicit_plan_from_semantic(self, semantic_plan: BuildPlan) -> List[Dict[str, Any]]:
        """
        BYGGER EN ENKEL TRÅDMODELL (för Milstolpe 1).
        Denna metod ignorerar komponenter och drar bara raka linjer mellan de
        noder som finns i den semantiska planen.
        """
        print("  -> Skapar enkel trådmodell från nod-koordinater...")
        explicit_primitives = []
        
        # Hämta alla noder från planen i rätt ordning
        node_ids_in_plan = [item['node_id'] for item in semantic_plan if item.get('type') == 'COMPONENT']

        if len(node_ids_in_plan) < 2:
            print("    -> VARNING: Planen har färre än två noder, kan inte skapa linjer.")
            return []

        # Loopa igenom nod-paren och skapa en 'LINE'-primitiv för varje par
        for i in range(len(node_ids_in_plan) - 1):
            start_node_id = node_ids_in_plan[i]
            end_node_id = node_ids_in_plan[i+1]

            start_coords = self.nodes_by_id[start_node_id].coords
            end_coords = self.nodes_by_id[end_node_id].coords

            explicit_primitives.append({
                'type': 'LINE',
                'start': start_coords,
                'end': end_coords
            })
            
        return explicit_primitives