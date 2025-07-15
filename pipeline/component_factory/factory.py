# pipeline/component_factory/factory.py
import math
import uuid
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
        "type": "BEND_90",
        "radius": 38.0,
        "center_to_end": 70.0
    },
    "BEND_45_SMS_38": {
        "type": "BEND_45",
        "radius": 38.0,
        "b_measure": 34.0  # B-måttet från ritningen
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

        return arc_start_pos, arc_mid_pos, arc_end_pos, outgoing_dir, dist_to_arcpoint


class Bend90(BaseBend):
    """ Expert-klass för 90-gradersböjar (TANGENT-ARC-TANGENT). """
    def __init__(self, node: BendNodeInfo, corner_pos: Vec3, incoming_dir: Vec3, radius: float, center_to_end: float):
        super().__init__(node, corner_pos, incoming_dir, radius)
        self.center_to_end = center_to_end

    def create_recipe(self) -> Tuple[List[Dict[str, Any]], Vec3, Vec3]:
        """ Bygger det specifika receptet för en 90-gradersböj. """
        # ---- KORRIGERINGEN ÄR HÄR ----
        # Vi tar nu emot 5 värden, och ignorerar det sista med `_`.
        arc_start, arc_mid, arc_end, outgoing_dir, _ = self._calculate_arc_geometry()

        # Formeln för 90-gradersböjar är enkel och använder inte dist_to_arcpoint
        tangent_length = self.center_to_end - self.radius
        if tangent_length < 0:
            tangent_length = 0
            
        # ... resten av koden i metoden är oförändrad ...
        component_id = f"bend_{uuid.uuid4().hex[:8]}"
        tangent1_start = arc_start - (self.incoming_dir * tangent_length)
        tangent2_end = arc_end + (outgoing_dir * tangent_length)

        recipe = []
        if tangent_length > 1e-6:
            recipe.append({
                'id': f"line_{uuid.uuid4().hex[:8]}",
                'component_id': component_id,
                'component_type': 'BEND_90',
                'type': 'LINE', 
                'start': tuple(vars(tangent1_start).values()), 
                'end': tuple(vars(arc_start).values())
            })
        
        recipe.append({
            'id': f"arc_{uuid.uuid4().hex[:8]}",
            'component_id': component_id,
            'component_type': 'BEND_90',
            'type': 'ARC', 
            'start': tuple(vars(arc_start).values()), 
            'mid': tuple(vars(arc_mid).values()), 
            'end': tuple(vars(arc_end).values())
        })
        
        if tangent_length > 1e-6:
            recipe.append({
                'id': f"line_{uuid.uuid4().hex[:8]}",
                'component_id': component_id,
                'component_type': 'BEND_90',
                'type': 'LINE', 
                'start': tuple(vars(arc_end).values()), 
                'end': tuple(vars(tangent2_end).values())
            })

        return recipe, tangent2_end, outgoing_dir


class Bend45(BaseBend):
    """ Expert-klass för 45-gradersböjar (TANGENT-ARC-TANGENT). """
    def __init__(self, node: BendNodeInfo, corner_pos: Vec3, incoming_dir: Vec3, radius: float, b_measure: float):
        super().__init__(node, corner_pos, incoming_dir, radius)
        self.b_measure = b_measure

    def create_recipe(self) -> Tuple[List[Dict[str, Any]], Vec3, Vec3]:
        """ Bygger det specifika receptet för en 45-gradersböj. """
        # Steg 1: Anropa basklassen för att få grundgeometrin.
        # Vi får nu även dist_to_arcpoint returnerat tack vare vår lilla justering.
        arc_start, arc_mid, arc_end, outgoing_dir, dist_to_arcpoint = self._calculate_arc_geometry()

        # Steg 2: Beräkna det sanna CTE-måttet från B-måttet.
        # CTE = B * sqrt(2)
        center_to_end = self.b_measure * math.sqrt(2)

        # Steg 3: Beräkna tangentlängd med den generella och korrekta formeln.
        # tangent_length = CTE - (avståndet från hörn till bågens startpunkt)
        tangent_length = center_to_end - dist_to_arcpoint
        if tangent_length < 0:
            print(f"VARNING: Negativ tangentlängd ({tangent_length:.2f}mm) beräknad för 45-gradersböj. Sätter till 0.")
            tangent_length = 0

        # Steg 4: Bygg det kompletta receptet med unika ID:n.
        component_id = f"bend_{uuid.uuid4().hex[:8]}"
        tangent1_start = arc_start - (self.incoming_dir * tangent_length)
        tangent2_end = arc_end + (outgoing_dir * tangent_length)

        recipe = []
        if tangent_length > 1e-6:
            recipe.append({
                'id': f"line_{uuid.uuid4().hex[:8]}",
                'component_id': component_id,
                'component_type': 'BEND_45',
                'type': 'LINE', 
                'start': tuple(vars(tangent1_start).values()), 
                'end': tuple(vars(arc_start).values())
            })
        
        recipe.append({
            'id': f"arc_{uuid.uuid4().hex[:8]}",
            'component_id': component_id,
            'component_type': 'BEND_45',
            'type': 'ARC', 
            'start': tuple(vars(arc_start).values()), 
            'mid': tuple(vars(arc_mid).values()), 
            'end': tuple(vars(arc_end).values())
        })
        
        if tangent_length > 1e-6:
            recipe.append({
                'id': f"line_{uuid.uuid4().hex[:8]}",
                'component_id': component_id,
                'component_type': 'BEND_45',
                'type': 'LINE', 
                'start': tuple(vars(arc_end).values()), 
                'end': tuple(vars(tangent2_end).values())
            })

        return recipe, tangent2_end, outgoing_dir


class CustomBend(BaseBend):
    """
    Expert-klass för specialkapade böjar.
    Simulerar en kapad 90-gradersböj med en fast tangentlängd.
    Receptet är [ARC, TANGENT] med en fast, förbestämd orientering.
    """
    def __init__(self, node: BendNodeInfo, corner_pos: Vec3, incoming_dir: Vec3, radius: float, center_to_end_90: float):
        super().__init__(node, corner_pos, incoming_dir, radius)
        # Tar emot CTE-måttet från en standard 90-gradersböj för att beräkna tangentlängd.
        self.center_to_end_90 = center_to_end_90

    def create_recipe(self) -> Tuple[List[Dict[str, Any]], Vec3, Vec3]:
        """ Bygger receptet för en specialkapad böj. """
        # Steg 1: Beräkna bågen baserat på nodens exakta vinkel.
        arc_start, arc_mid, arc_end, outgoing_dir, _ = self._calculate_arc_geometry()

        # Steg 2: Beräkna den fasta tangentlängden baserat på en 90-gradersböj.
        tangent_length = self.center_to_end_90 - self.radius
        if tangent_length < 0:
            tangent_length = 0

        # Steg 3: Bygg receptet med den fasta orienteringen [ARC, TANGENT].
        component_id = f"bend_{uuid.uuid4().hex[:8]}"
        tangent_end = arc_end + (outgoing_dir * tangent_length)

        recipe = []
        
        # Bågen först
        recipe.append({
            'id': f"arc_{uuid.uuid4().hex[:8]}",
            'component_id': component_id,
            'component_type': 'BEND_CUSTOM',
            'type': 'ARC', 
            'start': tuple(vars(arc_start).values()), 
            'mid': tuple(vars(arc_mid).values()), 
            'end': tuple(vars(arc_end).values())
        })
        
        # Sedan den enda tangenten
        if tangent_length > 1e-6:
            recipe.append({
                'id': f"line_{uuid.uuid4().hex[:8]}",
                'component_id': component_id,
                'component_type': 'BEND_CUSTOM',
                'type': 'LINE', 
                'start': tuple(vars(arc_end).values()), 
                'end': tuple(vars(tangent_end).values())
            })

        # Steg 4: Pennans nya position är i slutet på tangenten.
        return recipe, tangent_end, outgoing_dir


class ComponentFactory:
    """ Arbetsledaren som delegerar jobbet till rätt expert. """
    def __init__(self, catalog: Any = None):
        # Ignorerar katalogen för nu, vi använder MOCK_BEND_CATALOG.
        self.catalog = catalog

    def create_bend_recipe(self, node: BendNodeInfo, corner_pos: Vec3, incoming_dir: Vec3) -> Tuple[List[Dict[str, Any]], Vec3, Vec3]:
        """
        Dispatcher-metod. Väljer rätt expert (90, 45, eller Custom) baserat på vinkel.
        """
        print(f"   -> (Factory) Anropar expert för BÖJ vid nod {node.id[:8]} med vinkel {node.angle}...")
        
        component_data = None
        bend_expert = None

        # Välj expert baserat på vinkel
        if math.isclose(node.angle, 90.0):
            component_data = MOCK_BEND_CATALOG.get("BEND_90_SMS_38")
            if component_data:
                bend_expert = Bend90(
                    node=node, corner_pos=corner_pos, incoming_dir=incoming_dir,
                    radius=component_data['radius'], center_to_end=component_data['center_to_end']
                )
        elif math.isclose(node.angle, 45.0):
            component_data = MOCK_BEND_CATALOG.get("BEND_45_SMS_38")
            if component_data:
                bend_expert = Bend45(
                    node=node, corner_pos=corner_pos, incoming_dir=incoming_dir,
                    radius=component_data['radius'], b_measure=component_data['b_measure']
                )
        else: # "Catch-all" för alla andra vinklar
            # Hämta data från en standard 90-gradersböj för att kunna beräkna tangentlängden.
            component_data = MOCK_BEND_CATALOG.get("BEND_90_SMS_38")
            if component_data:
                bend_expert = CustomBend(
                    node=node, corner_pos=corner_pos, incoming_dir=incoming_dir,
                    radius=component_data['radius'], center_to_end_90=component_data['center_to_end']
                )

        # Kontrollera och exekvera
        if bend_expert and component_data:
            return bend_expert.create_recipe()
        
        # Fallback om något gick fel
        print(f"    -> FEL: Kunde inte skapa böj för nod {node.id[:8]}. Kontrollera vinkel ({node.angle}) och mock-data.")
        return [], corner_pos, incoming_dir