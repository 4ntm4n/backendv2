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
        
        # Steg 1: Initiera "3D-pennan" vid startpunkten. Denna del är kritisk.
        start_node_id = conceptual_plan[0]['id']
        start_node = self.nodes_by_id[start_node_id]

        self.pen_position = Vec3(*start_node.coords)
        if isinstance(start_node, EndpointNodeInfo):
            self.pen_direction = Vec3(*start_node.direction)
        else:
            # Om startpunkten inte är en ändpunkt, beräkna startriktning från nästa nod.
            next_node_id = conceptual_plan[2]['id']
            next_node = self.nodes_by_id[next_node_id]
            self.pen_direction = (Vec3(*next_node.coords) - Vec3(*start_node.coords)).normalize()

        # Steg 2: Loopa igenom planen och bygg komponenter.
        # Vi använder enumerate för att få tillgång till index (i), vilket behövs för custom-böjar.
        for i, item in enumerate(conceptual_plan):
            if item['type'] == 'NODE':
                node = self.nodes_by_id[item['id']]

                if isinstance(node, BendNodeInfo):
                    corner_pos = Vec3(*node.coords)

                    # Förbered argument för fabriken. Default är en tom dictionary.
                    kwargs_for_factory = {}
                    
                    # Om det är en "custom bend", fatta ett beslut och lägg till extra instruktioner.
                    if not math.isclose(node.angle, 90.0) and not math.isclose(node.angle, 45.0):
                        print(f"      -> Custom bend ({node.angle:.1f}°). Jämför avstånd till grann-noder:")

                        # --- START PÅ NY, SÄKRARE LOGIK ---
                        
                        # Hämta inkommande längd
                        incoming_length = conceptual_plan[i-1].get('length') if i > 0 else None
                        if incoming_length is not None:
                            print(f"         - Avstånd IN (från föregående nod): {incoming_length:.2f} mm")
                        else:
                            print(f"         - Avstånd IN (från föregående nod): Okänd (None)")

                        # Hämta utgående längd
                        outgoing_length = conceptual_plan[i+1].get('length') if i < len(conceptual_plan) - 1 else None
                        if outgoing_length is not None:
                            print(f"         - Avstånd UT (till nästa nod):    {outgoing_length:.2f} mm")
                        else:
                            print(f"         - Avstånd UT (till nästa nod):    Okänd (None)")

                        # Jämför längderna på ett säkert sätt
                        # Om en längd är okänd (None), behandla den som oändligt lång.
                        compare_in = incoming_length if incoming_length is not None else float('inf')
                        compare_out = outgoing_length if outgoing_length is not None else float('inf')

                        if compare_in < compare_out:
                            kwargs_for_factory['tangent_placement'] = 'INCOMING'
                            print(f"         -> BESLUT: Kortast avstånd IN. Tangent placeras på IN-sidan.")
                        else:
                            kwargs_for_factory['tangent_placement'] = 'OUTGOING'
                            print(f"         -> BESLUT: Kortast avstånd UT (eller lika/okänt). Tangent placeras på UT-sidan.")
                        
                        # --- SLUT PÅ NY, SÄKRARE LOGIK ---

                    component_recipe, new_pos, new_dir = self.factory.create_bend_recipe(
                        node, corner_pos, self.pen_direction, **kwargs_for_factory
                    )


                    # Lägg till alla delar från receptet till den slutgiltiga byggplanen.
                    if component_recipe:
                        drawing_plan.build_plan.extend(component_recipe)

                    # Uppdatera pennans position och riktning för nästa iteration.
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