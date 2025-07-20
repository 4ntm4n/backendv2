# pipeline/centerline_builder/builder.py

from typing import List, Dict, Any, Tuple
from pipeline.topology_builder.node_types_v2 import NodeInfo
from pipeline.shared.types import BuildPlanItem

import math
import uuid
from pipeline.topology_builder.builder import Vec3
from pipeline.topology_builder.node_types_v2 import BendNodeInfo, EndpointNodeInfo, TeeNodeInfo



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
        
        # Initiera "3D-pennan" vid startpunkten
        start_node_id = conceptual_plan[0]['id']
        start_node = self.nodes_by_id[start_node_id]
        self.pen_position = Vec3(*start_node.coords)
        if isinstance(start_node, EndpointNodeInfo):
            self.pen_direction = Vec3(*start_node.direction)
        else:
            next_node_id = conceptual_plan[2]['id']
            next_node = self.nodes_by_id[next_node_id]
            self.pen_direction = (Vec3(*next_node.coords) - Vec3(*start_node.coords)).normalize()

        # Loopa igenom planen och bygg komponenter
        for i, item in enumerate(conceptual_plan):
            if item['type'] == 'NODE':
                node = self.nodes_by_id[item['id']]
                component_recipe, new_pos, new_dir = None, None, None

                if isinstance(node, BendNodeInfo):
                    # ... (All kod för böjar är helt oförändrad) ...
                    corner_pos = Vec3(*node.coords)
                    kwargs_for_factory = {}
                    if not math.isclose(node.angle, 90.0) and not math.isclose(node.angle, 45.0):
                        incoming_length = conceptual_plan[i-1].get('length') if i > 0 else None
                        outgoing_length = conceptual_plan[i+1].get('length') if i < len(conceptual_plan) - 1 else None
                        compare_in = incoming_length if incoming_length is not None else float('inf')
                        compare_out = outgoing_length if outgoing_length is not None else float('inf')
                        if compare_in < compare_out:
                            kwargs_for_factory['tangent_placement'] = 'INCOMING'
                        else:
                            kwargs_for_factory['tangent_placement'] = 'OUTGOING'
                    component_recipe, new_pos, new_dir = self.factory.create_bend_recipe(node, corner_pos, self.pen_direction, **kwargs_for_factory)
                
                # --- ANROPA DEN NYA HJÄLPMETODEN ---
                elif isinstance(node, TeeNodeInfo):
                    component_recipe, new_pos, new_dir = self._handle_tee_node(node, conceptual_plan)

                # Gemensam logik för att uppdatera planen och pennan
                if component_recipe:
                    drawing_plan.build_plan.extend(component_recipe)
                    self.pen_position = new_pos
                    self.pen_direction = new_dir


    def _handle_tee_node(self, node: TeeNodeInfo, conceptual_plan: list) -> Tuple[List[Dict], Vec3, Vec3]:
        """
        UPPDATERAD HJÄLPMETOD: Hämtar nu kant-data direkt från topologin
        för att säkerställa att alla tre anslutningar analyseras korrekt.
        """
        center_pos = Vec3(*node.coords)
        print(f"   -> Hanterar T-RÖR vid nod {node.id[:8]}")

        # Steg 1: Hämta alla tre anslutna kanter direkt från topologi-grafen.
        # Detta är den enda källan till sanning.
        connected_edges_data = self.topology.edges(node.id, data=True)
        
        run_pipe_specs = []
        branch_pipe_spec = None

        # Steg 2: Iterera igenom de tre kanterna och sortera specifikationerna.
        for u, v, data in connected_edges_data:
            pipe_spec = data.get('pipe_spec')

            # --- NY DEBUG-LOGG ---
            print(f"      -> DEBUG: Inspekterar kant-data från grafen: {data}")
            # --- SLUT PÅ DEBUG-LOGG ---
            
            # Identifiera vilken granne som är på andra sidan av kanten
            neighbor_id = v if u == node.id else u
            
            if neighbor_id in node.run_node_ids:
                run_pipe_specs.append(pipe_spec)
            elif neighbor_id == node.branch_node_id:
                branch_pipe_spec = pipe_spec

        # Steg 3: Fatta ett beslut baserat på specifikationerna.
        main_run_spec = run_pipe_specs[0] if run_pipe_specs and run_pipe_specs[0] else ""
        
        # Debug-loggar för att verifiera
        print(f"      -> Analyserar anslutningar:")
        print(f"         - Run specs: {run_pipe_specs}")
        print(f"         - Branch spec: {branch_pipe_spec}")

        # Default-värden för ett standard T-rör
        tee_type_name = f"TEE_{main_run_spec}"
        kwargs_for_factory = {}

        # Om branch har en annan dimension, välj ett nedminskat T-rör
        if branch_pipe_spec and main_run_spec and branch_pipe_spec != main_run_spec:
            print(f"      -> Upptäckt dimensionsskillnad: Run är {main_run_spec}, Branch är {branch_pipe_spec}.")
            tee_type_name = f"REDUCED_TEE_{main_run_spec}"
            kwargs_for_factory['branch_pipe_spec'] = branch_pipe_spec
            print(f"      -> BESLUT: Använder {tee_type_name}.")
        else:
            print(f"      -> Inga dimensionsskillnader. BESLUT: Använder standard T-rör.")

        # Steg 4: Anropa fabriken med rätt instruktioner.
        kwargs_for_factory['tee_type_name'] = tee_type_name
        return self.factory.create_tee_recipe(
            node, center_pos, self.nodes_by_id, **kwargs_for_factory
        )

    

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