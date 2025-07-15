# pipeline/component_factory/factory.py
import math
from typing import List, Dict, Any, Tuple

# Importera de klasser och typer vi behöver
from pipeline.topology_builder.builder import Vec3
from pipeline.topology_builder.node_types_v2 import BendNodeInfo


# =================================================================
# === Steg 1: Isolerad Testdata (Mock-katalog) ===
# =================================================================
# Enkel, global "mock" för att simulera den riktiga produktkatalogen.
# Detta är vår enda sanningskälla för testdata.
MOCK_BEND_CATALOG = {
    "BEND_90_SMS_38": {
        "radius": 38.0,
        "center_to_end": 70.0  # CTE-mått
    }
}
# =================================================================


class BaseBend:
    """
    Ren beräkningsmotor för en böjs grundläggande geometri (bågen).
    Tar emot all nödvändig data som argument, har inga egna hårdkodade värden.
    """
    def __init__(self, node: BendNodeInfo, corner_pos: Vec3, incoming_dir: Vec3, radius: float):
        self.node = node
        self.corner_pos = corner_pos
        self.incoming_dir = incoming_dir
        self.radius = radius

    def _calculate_arc_geometry(self) -> Tuple[Vec3, Vec3, Vec3, Vec3]:
        """ Beräknar och returnerar: (arc_start, arc_mid, arc_end, outgoing_dir) """
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

        return arc_start_pos, arc_mid_pos, arc_end_pos, outgoing_dir


class Bend90(BaseBend):
    """ Expert-klass för 90-gradersböjar (TANGENT-ARC-TANGENT). """
    def __init__(self, node: BendNodeInfo, corner_pos: Vec3, incoming_dir: Vec3, radius: float, center_to_end: float):
        super().__init__(node, corner_pos, incoming_dir, radius)
        self.center_to_end = center_to_end

    def create_recipe(self) -> Tuple[List[Dict[str, Any]], Vec3, Vec3]:
        """ Bygger det specifika receptet för en 90-gradersböj. """
        arc_start, arc_mid, arc_end, outgoing_dir = self._calculate_arc_geometry()

        tangent_length = self.center_to_end - self.radius
        if tangent_length < 0:
            tangent_length = 0

        tangent1_start = arc_start - (self.incoming_dir * tangent_length)
        tangent2_end = arc_end + (outgoing_dir * tangent_length)

        recipe = []
        if tangent_length > 1e-6:
            recipe.append({'type': 'LINE', 'start': tuple(vars(tangent1_start).values()), 'end': tuple(vars(arc_start).values())})
        
        recipe.append({'type': 'ARC', 'start': tuple(vars(arc_start).values()), 'mid': tuple(vars(arc_mid).values()), 'end': tuple(vars(arc_end).values())})
        
        if tangent_length > 1e-6:
            recipe.append({'type': 'LINE', 'start': tuple(vars(arc_end).values()), 'end': tuple(vars(tangent2_end).values())})

        return recipe, tangent2_end, outgoing_dir


class ComponentFactory:
    """ Arbetsledaren som delegerar jobbet till rätt expert. """
    def __init__(self, catalog: Any = None):
        # Ignorerar katalogen för nu, vi använder MOCK_BEND_CATALOG.
        self.catalog = catalog

    def create_bend_recipe(self, node: BendNodeInfo, corner_pos: Vec3, incoming_dir: Vec3) -> Tuple[List[Dict[str, Any]], Vec3, Vec3]:
        """
        Dispatcher-metod. Hämtar data från mock-katalogen och anropar rätt expert.
        """
        print(f"   -> (Factory) Anropar expert för BÖJ vid nod {node.id[:8]}...")
        
        # TODO: Hårdkodat för att alltid välja vår enda test-böj.
        bend_type_name = "BEND_90_SMS_38"
        component_data = MOCK_BEND_CATALOG.get(bend_type_name)

        if not component_data:
            print(f"    -> FEL: Hittade inte '{bend_type_name}' i MOCK_BEND_CATALOG.")
            return [], corner_pos, incoming_dir

        # Välj expert och skicka med den specifika data som experten behöver.
        if "BEND_90" in bend_type_name:
            bend_expert = Bend90(
                node=node,
                corner_pos=corner_pos,
                incoming_dir=incoming_dir,
                radius=component_data['radius'],
                center_to_end=component_data['center_to_end']
            )
            return bend_expert.create_recipe()

        # Fallback om ingen expert hittas.
        print(f"    -> VARNING: Ingen expert-klass matchade '{bend_type_name}'.")
        return [], corner_pos, incoming_dir