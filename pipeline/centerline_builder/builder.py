# pipeline/centerline_builder/builder.py

from typing import List, Dict, Any
from pipeline.topology_builder.node_types_v2 import NodeInfo
from pipeline.shared.types import BuildPlanItem

import math
import uuid
from pipeline.topology_builder.builder import Vec3
from pipeline.topology_builder.node_types_v2 import BendNodeInfo, EndpointNodeInfo


# Lägg till denna klassdefinition
class DrawingPlan:
    """En container för den slutgiltiga bygghandlingen."""
    def __init__(self):
        self.build_plan = []
        self.assembly_map = {}

class CenterlineBuilder:
    """
    MODUL 5: Byggmästaren.
    Ansvarar för att omvandla en logisk resplan till en detaljerad,
    geometrisk bygghandling.
    
    (FÖR TILLFÄLLET: Implementerar en enkel översättning för att skapa en
    trådmodell för visualisering, precis som den gamla PlanAdjuster gjorde.)
    """
    def __init__(self, travel_plans: List[List[BuildPlanItem]], nodes: List[NodeInfo], topology: Any, catalog: Any, adjuster: Any, factory: Any):
        self.travel_plans = travel_plans
        self.nodes_by_id = {node.id: node for node in nodes}
        self.topology = topology
        self.catalog = catalog
        self.adjuster = adjuster

        self.factory = factory

        # "3D-pennans" tillstånd
        self.pen_position: Vec3 = None
        self.pen_direction: Vec3 = None

    def build_drawing_plans(self) -> List[List[Dict[str, Any]]]:
        """
        Huvudmetod som exekverar byggprocessen i två pass.
        Returnerar en lista av explicita planer, en för varje gren.
        """
        print("--- Modul 5 (CenterlineBuilder): Startar bygge av DrawingPlan ---")
        all_explicit_plans = []

        for conceptual_plan in self.travel_plans:
            drawing_plan = DrawingPlan()

            # Pass 1: Placera ut all komponentgeometri (just nu bara böjar)
            self._place_components(conceptual_plan, drawing_plan)

            # Pass 2: Anslut komponenterna med raka rör (implementeras senare)
            self._connect_components(conceptual_plan, drawing_plan)

            all_explicit_plans.append(drawing_plan.build_plan)

        return all_explicit_plans

    def _place_components(self, conceptual_plan: list, drawing_plan: DrawingPlan):
        """Pass 1: Loopar igenom resplanen och placerar komponenternas geometri."""
        print("   -> Pass 1: Placerar komponenter...")
        # Hitta startnod och initiera pennan
        start_node_id = conceptual_plan[0]['id']
        start_node = self.nodes_by_id[start_node_id]

        self.pen_position = Vec3(*start_node.coords)
        if isinstance(start_node, EndpointNodeInfo):
            self.pen_direction = Vec3(*start_node.direction)
        else:
            # Om startpunkten inte är en ändpunkt, beräkna startriktning
            next_node_id = conceptual_plan[2]['id']
            next_node = self.nodes_by_id[next_node_id]
            self.pen_direction = (Vec3(*next_node.coords) - Vec3(*start_node.coords)).normalize()

        # Loopa igenom planen för att hitta och bygga böjar
        for item in conceptual_plan:
            if item['type'] == 'NODE':
                node = self.nodes_by_id[item['id']]

                if isinstance(node, BendNodeInfo):
                    # Vi använder nodens koordinater som hörn-position
                    corner_pos = Vec3(*node.coords)

                    # Anropa fabriken för att få ett recept och pennans nya tillstånd
                    component_recipe, new_pos, new_dir = self.factory.create_bend_recipe(node, corner_pos, self.pen_direction)

                    # Lägg till alla delar från receptet till den slutgiltiga byggplanen.
                    if component_recipe:
                        drawing_plan.build_plan.extend(component_recipe)

                    # Uppdatera pennans position och riktning för nästa iteration
                    self.pen_position = new_pos
                    self.pen_direction = new_dir
                    
    def _connect_components(self, conceptual_plan: list, drawing_plan: DrawingPlan):
        """Pass 2: Ansluter komponenterna. IMPLEMENTERAS SENARE."""
        print("   -> Pass 2: Ansluter komponenter (hoppar över för nu).")
        pass

    def _create_explicit_plan_from_conceptual(self, conceptual_plan: List[BuildPlanItem]) -> List[Dict[str, Any]]:
        """
        TEMPORÄR METOD: Bygger en enkel trådmodell för visualisering.
        Denna metod ignorerar kanter och drar bara raka linjer mellan
        nodernas centrum-koordinater.
        """
        print("   -> (Visualiseringsläge: Skapar enkel trådmodell från nod-koordinater)")
        explicit_primitives = []

        # Hämta alla noder från planen i rätt ordning
        node_ids_in_plan = [item['id'] for item in conceptual_plan if item.get('type') == 'NODE']

        if len(node_ids_in_plan) < 2:
            return []

        # Loopa igenom nod-paren och skapa en 'LINE'-primitiv för varje par
        for i in range(len(node_ids_in_plan) - 1):
            start_node_id = node_ids_in_plan[i]
            end_node_id = node_ids_in_plan[i+1]

            start_node = self.nodes_by_id.get(start_node_id)
            end_node = self.nodes_by_id.get(end_node_id)

            if start_node and end_node:
                explicit_primitives.append({
                    'type': 'LINE',
                    'start': start_node.coords,
                    'end': end_node.coords
                })

        return explicit_primitives