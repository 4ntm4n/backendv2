# pipeline/component_factory/factory.py
import math
from typing import List, Dict, Any, Tuple

# Importera de klasser och typer vi behöver
from pipeline.topology_builder.builder import Vec3
from pipeline.topology_builder.node_types_v2 import BendNodeInfo

class ComponentFactory:
    def __init__(self, catalog: Any):
        self.catalog = catalog

    def create_bend_recipe(self, node: BendNodeInfo, corner_pos: Vec3, incoming_dir: Vec3) -> Tuple[List[Dict[str, Any]], Vec3, Vec3]:
        """
        Tar emot all nödvändig information och utför den rena matematiska
        beräkningen för att skapa ett "recept" för en böj.
        Returnerar en tuple med: (lista av primitiver, ny position, ny riktning).
        """
        print(f"   -> (Factory) Beräknar geometri för BÖJ vid nod {node.id[:8]}...")

        # === Detta är den gamla, beprövade matematiken, nu på rätt plats ===
        radius = 38.0
        angle = node.angle

        v1 = Vec3(*node.vectors[0])
        v2 = Vec3(*node.vectors[1])
        outgoing_dir = v2 if (-incoming_dir).dot(v1) > (-incoming_dir).dot(v2) else v1

        internal_angle_rad = math.pi - math.radians(angle)
        dist_to_arcpoint = radius / math.tan(internal_angle_rad / 2.0)

        arc_start_pos = corner_pos - (incoming_dir * dist_to_arcpoint)
        arc_end_pos = corner_pos + (outgoing_dir * dist_to_arcpoint)

        dist_to_center = radius / math.sin(internal_angle_rad / 2.0)
        bisection_vec = ((-incoming_dir) + outgoing_dir).normalize()
        arc_center = corner_pos + bisection_vec * dist_to_center

        midpoint_of_chord = (arc_start_pos + arc_end_pos) * 0.5
        vec_center_to_mid_chord = (midpoint_of_chord - arc_center).normalize()
        arc_mid_pos = arc_center + vec_center_to_mid_chord * radius
        # =================================================================

        # Skapa den explicita primitiva instruktionen
        arc_primitive = {
            'type': 'ARC',
            'start': tuple(vars(arc_start_pos).values()),
            'mid': tuple(vars(arc_mid_pos).values()),
            'end': tuple(vars(arc_end_pos).values()),
        }

        # Returnera ett komplett recept (en lista) och pennans nya tillstånd
        return [arc_primitive], arc_end_pos, outgoing_dir