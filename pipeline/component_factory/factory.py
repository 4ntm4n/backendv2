# pipeline/component_factory/factory.py
import math
import uuid
from typing import List, Dict, Any, Tuple

# Importera de klasser och typer vi behöver
from pipeline.topology_builder.builder import Vec3
from pipeline.topology_builder.node_types_v2 import BendNodeInfo, TeeNodeInfo, NodeInfo


# =================================================================
# === Steg 1: Isolerad Testdata (Mock-katalog) ===
# =================================================================
# Enkel, global "mock" för att simulera den riktiga produktkatalogen.
# Detta är vår enda sanningskälla för testdata.
MOCK_COMPONENT_CATALOG = {
    "BEND_90_SMS_38": {
        "type": "BEND_90", "radius": 38.0, "center_to_end": 70.0
    },
    "BEND_45_SMS_38": {
        "type": "BEND_45", "radius": 38.0, "b_measure": 34.0
    },
    "TEE_SMS_38": {
        "type": "TEE", "branch_cte": 70.0, "run_cte": 70.0
    },
    "SHORT_TEE_SMS_38": {
        "type": "TEE", "branch_cte": 70.0, "run_cte": 21.0
    },
    
    "REDUCED_TEE_SMS_38": {
        "type": "REDUCED_TEE",
        "run_cte": 70.0,  # Huvudröret är fortfarande standard
        "branch_options": {
            "SMS_25": { "branch_cte": 60.0 }, # Exempel på A-mått för 25mm avstick
            "SMS_18": { "branch_cte": 55.0 },
            "SMS_12": { "branch_cte": 50.0 }
        }
    },
    "SHORT_REDUCED_TEE_SMS_38": {
    "type": "REDUCED_TEE",
    "run_cte": 70.0,
    "branch_options": {
        "SMS_25": { "branch_cte": 21.0 },
        "SMS_18": { "branch_cte": 21.0 },
        "SMS_12": { "branch_cte": 21.0 }
        }
    }
    #skapa komponent för konor (kanske inte ens behövs)
}


# =================================================================

# =================================================================
# === Klasser för olika typer av böjar ===
# =================================================================

class BaseBend:
    """
    Basklass för alla böjar. Innehåller nu all gemensam logik för
    att beräkna geometri OCH bygga det slutgiltiga receptet.
    """
    def __init__(self, node: BendNodeInfo, corner_pos: Vec3, incoming_dir: Vec3, radius: float):
        self.node = node
        self.corner_pos = corner_pos
        self.incoming_dir = incoming_dir
        self.radius = radius
        # Subklasser förväntas sätta detta värde.
        self.component_type = 'BEND_BASE' 

    def _calculate_arc_geometry(self) -> Tuple[Vec3, Vec3, Vec3, Vec3, float]:
        """ Beräknar och returnerar: (arc_start, arc_mid, arc_end, outgoing_dir, dist_to_arcpoint) """
        # (Denna metod är oförändrad)
        angle = self.node.angle
        v1 = Vec3(*self.node.vectors[0])
        v2 = Vec3(*self.node.vectors[1])

        outgoing_dir = v2 if (-self.incoming_dir).dot(v1) > (-self.incoming_dir).dot(v2) else v1

        internal_angle_rad = math.pi - math.radians(angle)
        dist_to_arcpoint = self.radius / math.tan(internal_angle_rad / 2.0)

        arc_start_pos = self.corner_pos - (self.incoming_dir * dist_to_arcpoint)
        arc_end_pos = self.corner_pos + (outgoing_dir * dist_to_arcpoint)

        dist_to_center = self.radius / math.sin(internal_angle_rad / 2.0)
        bisection_vec = ((-self.incoming_dir) + outgoing_dir).normalize()
        arc_center = self.corner_pos + bisection_vec * dist_to_center

        midpoint_of_chord = (arc_start_pos + arc_end_pos) * 0.5
        vec_center_to_mid_chord = (midpoint_of_chord - arc_center).normalize()
        arc_mid_pos = arc_center + vec_center_to_mid_chord * self.radius

        return arc_start_pos, arc_mid_pos, arc_end_pos, outgoing_dir, dist_to_arcpoint

    def _build_recipe_from_tangents(
        self,
        arc_start: Vec3, arc_mid: Vec3, arc_end: Vec3, outgoing_dir: Vec3,
        tangent_in_len: float = 0.0, tangent_out_len: float = 0.0
         ) -> Tuple[List[Dict[str, Any]], Vec3, Vec3]:
        """
        NY, KORRIGERAD HJÄLPMETOD: Bygger det kompletta receptet och
        lägger BARA till tangenter om deras längd är större än noll.
        """
        component_id = f"bend_{uuid.uuid4().hex[:8]}"
        recipe = []
        
        # Pennans startposition är som standard i slutet av bågen
        new_pen_position = arc_end

        # Bygg inkommande tangent BARA om längden är meningsfull
        if tangent_in_len > 1e-6:
            start_pos = arc_start - (self.incoming_dir * tangent_in_len)
            recipe.append({'id': f"line_{uuid.uuid4().hex[:8]}", 'component_id': component_id, 'component_type': self.component_type, 'type': 'LINE', 'start': tuple(vars(start_pos).values()), 'end': tuple(vars(arc_start).values())})
        
        # Lägg alltid till den centrala bågen
        recipe.append({'id': f"arc_{uuid.uuid4().hex[:8]}", 'component_id': component_id, 'component_type': self.component_type, 'type': 'ARC', 'start': tuple(vars(arc_start).values()), 'mid': tuple(vars(arc_mid).values()), 'end': tuple(vars(arc_end).values())})

        # Bygg utgående tangent BARA om längden är meningsfull
        if tangent_out_len > 1e-6:
            end_pos = arc_end + (outgoing_dir * tangent_out_len)
            recipe.append({'id': f"line_{uuid.uuid4().hex[:8]}", 'component_id': component_id, 'component_type': self.component_type, 'type': 'LINE', 'start': tuple(vars(arc_end).values()), 'end': tuple(vars(end_pos).values())})
            # Om vi har en utgående tangent, är det den som bestämmer pennans nya position
            new_pen_position = end_pos

        return recipe, new_pen_position, outgoing_dir

class Bend90(BaseBend):
    """ Expert-klass för 90-gradersböjar. Extremt förenklad. """
    def __init__(self, node: BendNodeInfo, corner_pos: Vec3, incoming_dir: Vec3, radius: float, center_to_end: float):
        super().__init__(node, corner_pos, incoming_dir, radius)
        self.center_to_end = center_to_end
        self.component_type = 'BEND_90'

    def create_recipe(self) -> Tuple[List[Dict[str, Any]], Vec3, Vec3]:
        arc_start, arc_mid, arc_end, outgoing_dir, _ = self._calculate_arc_geometry()
        tangent_length = max(0, self.center_to_end - self.radius)
        return self._build_recipe_from_tangents(arc_start, arc_mid, arc_end, outgoing_dir, tangent_in_len=tangent_length, tangent_out_len=tangent_length)

class Bend45(BaseBend):
    """ Expert-klass för 45-gradersböjar. Extremt förenklad. """
    def __init__(self, node: BendNodeInfo, corner_pos: Vec3, incoming_dir: Vec3, radius: float, b_measure: float):
        super().__init__(node, corner_pos, incoming_dir, radius)
        self.b_measure = b_measure
        self.component_type = 'BEND_45'

    def create_recipe(self) -> Tuple[List[Dict[str, Any]], Vec3, Vec3]:
        arc_start, arc_mid, arc_end, outgoing_dir, dist_to_arcpoint = self._calculate_arc_geometry()
        center_to_end = self.b_measure * math.sqrt(2)
        tangent_length = max(0, center_to_end - dist_to_arcpoint)
        return self._build_recipe_from_tangents(arc_start, arc_mid, arc_end, outgoing_dir, tangent_in_len=tangent_length, tangent_out_len=tangent_length)

class CustomBend(BaseBend):
    """ Expert-klass för specialkapade böjar. Extremt förenklad. """
    def __init__(self, node: BendNodeInfo, corner_pos: Vec3, incoming_dir: Vec3, radius: float, center_to_end_90: float, tangent_placement: str):
        super().__init__(node, corner_pos, incoming_dir, radius)
        self.center_to_end_90 = center_to_end_90
        self.tangent_placement = tangent_placement
        self.component_type = 'BEND_CUSTOM'

    def create_recipe(self) -> Tuple[List[Dict[str, Any]], Vec3, Vec3]:
        arc_start, arc_mid, arc_end, outgoing_dir, _ = self._calculate_arc_geometry()
        tangent_length = max(0, self.center_to_end_90 - self.radius)
        
        tangent_in = tangent_length if self.tangent_placement == 'INCOMING' else 0.0
        tangent_out = tangent_length if self.tangent_placement == 'OUTGOING' else 0.0
        
        return self._build_recipe_from_tangents(arc_start, arc_mid, arc_end, outgoing_dir, tangent_in_len=tangent_in, tangent_out_len=tangent_out)


# =================================================================
# === Klasser för olika typer av T-rör ===
# =================================================================

class BaseTee:
    """
    Basklass för T-rör. Innehåller nu all gemensam logik för att
    beräkna riktningar OCH bygga det slutgiltiga receptet.
    """
    def __init__(self, node: TeeNodeInfo, center_pos: Vec3):
        self.node = node
        self.center_pos = center_pos
        self.component_type = 'TEE_BASE'

    def _get_directions(self, nodes_by_id: Dict[str, NodeInfo]) -> Dict[str, Vec3]:
        # (Denna metod är oförändrad)
        run_node_1 = nodes_by_id[self.node.run_node_ids[0]]
        run_node_2 = nodes_by_id[self.node.run_node_ids[1]]
        branch_node = nodes_by_id[self.node.branch_node_id]

        dir_run_1 = (Vec3(*run_node_1.coords) - self.center_pos).normalize()
        dir_run_2 = (Vec3(*run_node_2.coords) - self.center_pos).normalize()
        dir_branch = (Vec3(*branch_node.coords) - self.center_pos).normalize()

        return {"run1": dir_run_1, "run2": dir_run_2, "branch": dir_branch}

    def _build_recipe(self, nodes_by_id: Dict[str, NodeInfo], run_tangent_len: float, branch_tangent_len: float) -> Tuple[List[Dict[str, Any]], Vec3, Vec3]:
        """
        NY HJÄLPMETOD: Bygger det kompletta receptet baserat på tangentlängder.
        Detta eliminerar all kodduplicering från subklasserna.
        """
        directions = self._get_directions(nodes_by_id)
        component_id = f"tee_{uuid.uuid4().hex[:8]}"
        recipe = []

        # Skapa de två "run"-tangenterna
        run1_end = self.center_pos + (directions['run1'] * run_tangent_len)
        recipe.append({'id': f"line_{uuid.uuid4().hex[:8]}", 'component_id': component_id, 'component_type': self.component_type, 'type': 'LINE', 'start': tuple(vars(self.center_pos).values()), 'end': tuple(vars(run1_end).values())})

        run2_end = self.center_pos + (directions['run2'] * run_tangent_len)
        recipe.append({'id': f"line_{uuid.uuid4().hex[:8]}", 'component_id': component_id, 'component_type': self.component_type, 'type': 'LINE', 'start': tuple(vars(self.center_pos).values()), 'end': tuple(vars(run2_end).values())})

        # Skapa "branch"-tangenten
        branch_end = self.center_pos + (directions['branch'] * branch_tangent_len)
        recipe.append({'id': f"line_{uuid.uuid4().hex[:8]}", 'component_id': component_id, 'component_type': self.component_type, 'type': 'LINE', 'start': tuple(vars(self.center_pos).values()), 'end': tuple(vars(branch_end).values())})
        
        # Pennans tillstånd efter ett T-rör är speciellt. Vi återgår till centrum.
        return recipe, self.center_pos, directions['run1']

class TeeEqual(BaseTee):
    """ Expert-klass för ett standard, liksidigt T-rör. Nu förenklad. """
    def __init__(self, node: TeeNodeInfo, center_pos: Vec3, run_cte: float, branch_cte: float):
        super().__init__(node, center_pos)
        self.run_tangent_len = run_cte
        self.branch_tangent_len = branch_cte
        self.component_type = 'TEE'

    def create_recipe(self, nodes_by_id: Dict[str, NodeInfo]) -> Tuple[List[Dict[str, Any]], Vec3, Vec3]:
        # Anropar bara hjälpmetoden med sina specifika mått.
        return self._build_recipe(nodes_by_id, self.run_tangent_len, self.branch_tangent_len)

class TeeReduced(BaseTee):
    """ Expert-klass för ett nedminskat T-rör. Nu förenklad. """
    def __init__(self, node: TeeNodeInfo, center_pos: Vec3, run_cte: float, branch_cte: float):
        super().__init__(node, center_pos)
        self.run_tangent_len = run_cte
        self.branch_tangent_len = branch_cte
        self.component_type = 'REDUCED_TEE'

    def create_recipe(self, nodes_by_id: Dict[str, NodeInfo]) -> Tuple[List[Dict[str, Any]], Vec3, Vec3]:
        # Anropar bara hjälpmetoden med sina specifika mått.
        return self._build_recipe(nodes_by_id, self.run_tangent_len, self.branch_tangent_len)
# =================================================================

# =================================================================
# === Klasser för olika typer av konor (reducers) ===
# =================================================================

# TODO
# 1.1 skapa basklass för konor 
# 1.2 skapa subklass för koncentriska konor
# 2 (senare skapar vi subklass för excentriska konor)

# =================================================================
# === Huvudklass som anropas av centerline_builder ===
# =================================================================
class ComponentFactory:
    """ Arbetsledaren som delegerar jobbet till rätt expert. """
    def __init__(self, catalog: Any = None):
        # Ignorerar katalogen för nu, vi använder MOCK_COMPONENT_CATALOG.
        self.catalog = catalog
    

    def create_bend_recipe(self, node: BendNodeInfo, corner_pos: Vec3, incoming_dir: Vec3, tangent_placement: str = 'OUTGOING') -> Tuple[List[Dict[str, Any]], Vec3, Vec3]:
        """
        Dispatcher-metod. Väljer rätt expert (90, 45, eller Custom) baserat på vinkel.
        """
        print(f"   -> (Factory) Anropar expert för BÖJ vid nod {node.id[:8]} med vinkel {node.angle}...")
        
        component_data = None
        bend_expert = None

        # Välj expert baserat på vinkel
        if math.isclose(node.angle, 90.0):
            component_data = MOCK_COMPONENT_CATALOG.get("BEND_90_SMS_38")
            if component_data:
                bend_expert = Bend90(
                    node=node, corner_pos=corner_pos, incoming_dir=incoming_dir,
                    radius=component_data['radius'], center_to_end=component_data['center_to_end']
                )
        elif math.isclose(node.angle, 45.0):
            component_data = MOCK_COMPONENT_CATALOG.get("BEND_45_SMS_38")
            if component_data:
                bend_expert = Bend45(
                    node=node, corner_pos=corner_pos, incoming_dir=incoming_dir,
                    radius=component_data['radius'], b_measure=component_data['b_measure']
                )
        else: # "Catch-all" för alla andra vinklar
            component_data = MOCK_COMPONENT_CATALOG.get("BEND_90_SMS_38")
            if component_data:
                bend_expert = CustomBend(
                    node=node, corner_pos=corner_pos, incoming_dir=incoming_dir,
                    radius=component_data['radius'], 
                    center_to_end_90=component_data['center_to_end'],
                    tangent_placement=tangent_placement  # Skicka vidare instruktionen
                )

        # Kontrollera och exekvera
        if bend_expert and component_data:
            return bend_expert.create_recipe()
        
        # Fallback om något gick fel
        print(f"    -> FEL: Kunde inte skapa böj för nod {node.id[:8]}. Kontrollera vinkel ({node.angle}) och mock-data.")
        return [], corner_pos, incoming_dir

    def create_tee_recipe(
        self, 
        node: TeeNodeInfo, 
        center_pos: Vec3, 
        nodes_by_id: Dict[str, NodeInfo],
        tee_type_name: str,          # T.ex. "TEE_SMS_38" eller "REDUCED_TEE_SMS_38"
        branch_pipe_spec: str = None # T.ex. "SMS_25", behövs bara för nedminskade
    ) -> Tuple[List[Dict[str, Any]], Vec3, Vec3]:
        """
        Uppdaterad dispatcher för T-rör. Hanterar nu både vanliga och nedminskade.
        """
        print(f"   -> (Factory) Anropar expert för T-RÖR vid nod {node.id[:8]} med typ '{tee_type_name}'...")
        
        component_data = MOCK_COMPONENT_CATALOG.get(tee_type_name)

        if not component_data:
            print(f"    -> FEL: Hittade inte '{tee_type_name}' i MOCK_COMPONENT_CATALOG.")
            return [], center_pos, Vec3(1, 0, 0)

        # Välj och instansiera rätt expert-klass.
        component_type = component_data.get('type')
        tee_expert = None

        if component_type == "TEE":
            tee_expert = TeeEqual(
                node=node,
                center_pos=center_pos,
                run_cte=component_data['run_cte'],
                branch_cte=component_data['branch_cte']
            )
        
        elif component_type == "REDUCED_TEE":
            # Hämta de specifika måtten för den valda branch-storleken
            branch_options = component_data.get('branch_options', {})
            selected_branch_data = branch_options.get(branch_pipe_spec)

            if not selected_branch_data:
                print(f"    -> FEL: Hittade inte branch-spec '{branch_pipe_spec}' för '{tee_type_name}'.")
                return [], center_pos, Vec3(1, 0, 0)

            tee_expert = TeeReduced(
                node=node,
                center_pos=center_pos,
                run_cte=component_data['run_cte'],
                branch_cte=selected_branch_data['branch_cte']
            )

        if tee_expert:
            return tee_expert.create_recipe(nodes_by_id)
        
        print(f"    -> VARNING: Ingen expert-klass matchade typen '{component_type}'.")
        return [], center_pos, Vec3(1, 0, 0)