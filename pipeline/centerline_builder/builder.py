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

    def _create_arc_for_bend(self, node: BendNodeInfo, corner_pos: Vec3, incoming_dir: Vec3, drawing_plan: DrawingPlan):
        """
        HÅRDKODAD: Skapar enbart en ARC med 38mm radie för en böj.
        Denna version använder korrekt geometri för att undvika inverterade bågar.
        Returnerar pennans nya position och riktning efter böjen.
        """
        # --- DEBUG-LOGGAR (DEL 1) ---
        print("\n--- DEBUG: _create_arc_for_bend ---")
        print(f"Hörn-nod ID: {node.id[:8]}, Position: ({corner_pos.x:.2f}, {corner_pos.y:.2f}, {corner_pos.z:.2f})")
        print(f"Förväntad vinkel: {node.angle:.2f} grader")
        print(f"Inkommande riktning: ({incoming_dir.x:.2f}, {incoming_dir.y:.2f}, {incoming_dir.z:.2f})")
        # --------------------------------

        # --- Steg 1: Hämta riktningar ---
        v1 = Vec3(*node.vectors[0])
        v2 = Vec3(*node.vectors[1])
        if (-incoming_dir).dot(v1) > (-incoming_dir).dot(v2):
            outgoing_dir = v2
        else:
            outgoing_dir = v1
        
        # --- DEBUG-LOGGAR (DEL 2) ---
        print(f"  -> Beräknad utgående riktning: ({outgoing_dir.x:.2f}, {outgoing_dir.y:.2f}, {outgoing_dir.z:.2f})")
        # --------------------------------

        # --- Steg 2: Korrekt geometrisk beräkning ---
        radius = 38.0
        # Konvertera deflektionsvinkeln (t.ex. 45°) till den interna geometriska vinkeln (180 - 45 = 135°)
        internal_angle_rad = math.pi - math.radians(node.angle)

        # Använd den korrekta interna vinkeln i alla efterföljande beräkningar
        dist_to_tangent_point = radius / math.tan(internal_angle_rad / 2.0)

        #dist_to_tangent_point = radius / math.tan(angle_rad / 2.0)
        arc_start_pos = corner_pos - (incoming_dir * dist_to_tangent_point)
        arc_end_pos = corner_pos + (outgoing_dir * dist_to_tangent_point)

        # --- DEBUG-LOGGAR (DEL 3) ---
        print(f"  -> Avstånd till tangentpunkt: {dist_to_tangent_point:.2f}")
        print(f"  -> Bågens startposition: ({arc_start_pos.x:.2f}, {arc_start_pos.y:.2f}, {arc_start_pos.z:.2f})")
        print(f"  -> Bågens slutposition: ({arc_end_pos.x:.2f}, {arc_end_pos.y:.2f}, {arc_end_pos.z:.2f})")
        # --------------------------------

        # Beräkna bågens centrum på ett robust sätt
        v_in = -incoming_dir
        v_out = outgoing_dir
        bisection_vec = (v_in + v_out).normalize()
        dist_to_center = radius / math.sin(internal_angle_rad / 2.0)
        arc_center = corner_pos + bisection_vec * dist_to_center

        # Beräkna en punkt mitt på bågen på ett robust sätt
        midpoint_of_chord = (arc_start_pos + arc_end_pos) * 0.5
        vec_center_to_mid_chord = (midpoint_of_chord - arc_center).normalize()
        arc_mid_pos = arc_center + vec_center_to_mid_chord * radius

        # --- DEBUG-LOGGAR (DEL 4) ---
        print(f"  -> Bågens centrum: ({arc_center.x:.2f}, {arc_center.y:.2f}, {arc_center.z:.2f})")
        print(f"  -> Bågens mittpunkt: ({arc_mid_pos.x:.2f}, {arc_mid_pos.y:.2f}, {arc_mid_pos.z:.2f})")
        # --------------------------------

        # --- Steg 3: Skapa den explicita primitiva instruktionen ---
        primitive = {
            'type': 'ARC',
            'start': (arc_start_pos.x, arc_start_pos.y, arc_start_pos.z),
            'mid': (arc_mid_pos.x, arc_mid_pos.y, arc_mid_pos.z),
            'end': (arc_end_pos.x, arc_end_pos.y, arc_end_pos.z)
        }
        drawing_plan.build_plan.append(primitive)

        print(f"      -> Skapade ARC-primitiv för nod {node.id[:8]}")

        # --- Steg 4: Returnera pennans nya tillstånd ---
        return arc_end_pos, outgoing_dir

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