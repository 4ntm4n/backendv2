import math
import copy
from typing import Dict, Any, List, Tuple
import networkx as nx


# Importera våra egna typer och klasser
from components_catalog.loader import CatalogLoader, ComponentData, Bend90Data, Bend45Data
from pipeline.topology_builder.node_types_v2 import NodeInfo, BendNodeInfo, TeeNodeInfo, EndpointNodeInfo
from pipeline.shared.types import BuildPlan, BuildPlanItem

class ImpossibleBuildError(Exception):
    """Ett anpassat fel som kastas när en design är geometriskt omöjlig."""
    pass

class PlanAdjuster:
    """
    MODUL 4: Geometri-Ingenjören.
    Ansvar: Att omvandla en semantisk byggplan till en geometriskt
    explicit ritning som är redo att skickas till den "dumma" executorn.
    """
    def __init__(self, semantic_plans: List[BuildPlan], nodes: List[NodeInfo], topology: nx.Graph, catalog: CatalogLoader):
        self.semantic_plans = semantic_plans
        self.nodes_by_id = {node.id: node for node in nodes}
        self.topology = topology # Behövs ej just nu, men kan behövas för framtida logik
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
        Innehåller den "mentala 3D-pennan". Itererar genom den semantiska planen
        och genererar en lista av geometriska primitiv (LINE, ARC).
        """
        # TODO: Implementera den fullständiga "3D-penna"-logiken här.
        # Detta är nästa steg i vår utveckling.
        
        print("  -> Bearbetar semantisk plan för att skapa geometriska primitiv...")
        
        # För nu, returnera bara en tom lista för att få bort AttributeError.
        # Nästa fel vi ser kommer att vara ett AssertionError från vårt test.
        explicit_primitives = []
        
        return explicit_primitives

    def _get_tangent_dist(self, component_item: BuildPlanItem) -> float:
        """
        Hjälpmetod för att beräkna en komponents tangent-distans (dess "take-up").
        Detta är avståndet från den teoretiska hörnpunkten till där det raka röret börjar.
        """
        # Endpoints har ingen take-up in i ett segment
        if component_item.get('component_name') == 'ENDPOINT':
            return 0.0

        spec = self.catalog.get_spec(component_item['spec_name'])
        if not spec: return 0.0
        
        comp_name_full = component_item.get('component_name', '')
        base_comp_name = "BEND_90" if "BEND_90" in comp_name_full else "BEND_45" if "BEND_45" in comp_name_full else comp_name_full
        
        comp_obj = spec.components.get(base_comp_name)
        if not comp_obj or not hasattr(comp_obj, 'bend_radius'):
            return 0.0
            
        node = self.nodes_by_id.get(component_item['node_id'])
        if not node or not hasattr(node, 'angle'): return 0.0
        
        angle_rad = math.radians(node.angle)
        # Formel: R / tan(yttre_vinkel / 2)
        if angle_rad <= 1e-6 or abs(math.tan(angle_rad / 2.0)) < 1e-6:
             return 0.0
        
        return abs(comp_obj.bend_radius / math.tan(angle_rad / 2.0))

    
    # TODO: Här kommer vi senare att lägga till hjälpmetoder för att
    # beräkna böjar och hantera underskott.
    # def _calculate_bend_geometry(...)
    # def _handle_shortfall(...)