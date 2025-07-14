# pipeline/2_topology_builder/builder.py

import math
from decimal import Decimal # <-- LÄGG TILL DENNA RAD
from typing import Dict, Any, List, Tuple
import networkx as nx

# Importera från andra V2-moduler
from components_catalog.loader import CatalogLoader
from .node_types_v2 import NodeInfo, BendNodeInfo, TeeNodeInfo, EndpointNodeInfo

# =====================================================================
# ### NYTT: Enkel, FreeCAD-fri 3D-vektor-klass för intern matematik ###
class Vec3:
    """En enkel, fristående 3D-vektor-klass för interna beräkningar."""
    def __init__(self, x=0.0, y=0.0, z=0.0):
        self.x, self.y, self.z = float(x), float(y), float(z)

    def __sub__(self, other):
        return Vec3(self.x - other.x, self.y - other.y, self.z - other.z)
    
    def __add__(self, other):
        return Vec3(self.x + other.x, self.y + other.y, self.z + other.z)

    def __mul__(self, scalar):
        return Vec3(self.x * scalar, self.y * scalar, self.z * scalar)

    def __neg__(self):
        """Returnerar en inverterad version av vektorn."""
        return Vec3(-self.x, -self.y, -self.z)

    def get_length(self):
        return math.sqrt(self.x**2 + self.y**2 + self.z**2)

    def normalize(self):
        length = self.get_length()
        if length == 0: return Vec3()
        return Vec3(self.x / length, self.y / length, self.z / length)

    def dot(self, other):
        return self.x * other.x + self.y * other.y + self.z * other.z
# =====================================================================


class TopologyBuilder:
    """
    Bygger en intelligent, berikad 3D-topologi från ren skissdata.
    """
    def __init__(self, parsed_sketch: Dict[str, Any], catalog: CatalogLoader):
        self.parsed_sketch = parsed_sketch
        self.catalog = catalog
        self.topology = nx.Graph()
        self.nodes: List[NodeInfo] = []
        # Denna är för testet
        self.coord_map_2d_to_node_id: Dict[Tuple[Decimal, Decimal], str] = {}
        # Denna används för att bygga 3D-geometrin
        self.point_2d_to_3d: Dict[Tuple[Decimal, Decimal], Vec3] = {}


    def build(self) -> Tuple[List[NodeInfo], nx.Graph]:
        """Huvudmetod som kör hela byggprocessen."""
        print("--- Modul 2 (Topology Builder): Startar ---")

        three_d_segments = self._translate_2d_to_3d()
        print(f"  -> Steg 1: {len(three_d_segments)} 3D-segment skapade.")

        self._build_graph(three_d_segments)
        print(f"  -> Steg 2: Graf skapad med {self.topology.number_of_nodes()} noder och {self.topology.number_of_edges()} kanter.")

        # LÄGG TILL DETTA ANROP INNAN _enrich_nodes
        self._cleanup_graph()

        self._enrich_nodes()
        print(f"  -> Steg 3 & 4: Noder klassificerade och berikade.")
        
        print("--- Topology Builder: Klar ---")
        return self.nodes, self.topology



    def _get_3d_direction_from_angle(self, angle_deg: float) -> Vec3:
        """
        Omvandlar en 2D-isometrisk vinkel till en normaliserad 3D-riktningsvektor.
        """
        angle_deg = angle_deg % 360
        standard_directions = {
            30.0:  Vec3(1.0, 0.0, 0.0),    # +X
            90.0:  Vec3(0.0, 0.0, -1.0),   # -Z
            150.0: Vec3(0.0, -1.0, 0.0),   # -Y
            210.0: Vec3(-1.0, 0.0, 0.0),   # -X
            270.0: Vec3(0.0, 0.0, 1.0),    # +Z
            330.0: Vec3(0.0, 1.0, 0.0)     # +Y
        }


        def angle_distance(a1, a2):
            phi = abs(a2 - a1) % 360
            return min(phi, 360 - phi)
        closest_angle = min(standard_directions.keys(), key=lambda std_angle: angle_distance(std_angle, angle_deg))
        snapped_direction = standard_directions[closest_angle]
        if not math.isclose(closest_angle, angle_deg, abs_tol=1.0):
            print(f"    -> INFO: Vinkel {angle_deg:.1f}° tolkad som närmsta standardvinkel {closest_angle}°.")
        return snapped_direction

    def _create_preliminary_2d_graph(self, segments: List[Dict[str, Any]]) -> nx.Graph:
        """
        Skapar en enkel graf baserad på 2D-koordinater för att förstå
        topologin innan 3D-översättning. Noderna är 2D-koordinat-nycklar.
        """
        g = nx.Graph()
        for segment in segments:
            start_2d = segment["start_point"]
            end_2d = segment["end_point"]

            start_x = start_2d['x'] if isinstance(start_2d, dict) else start_2d[0]
            start_y = start_2d['y'] if isinstance(start_2d, dict) else start_2d[1]
            end_x = end_2d['x'] if isinstance(end_2d, dict) else end_2d[0]
            end_y = end_2d['y'] if isinstance(end_2d, dict) else end_2d[1]

            start_key = (Decimal(str(start_x)), Decimal(str(start_y)))
            end_key = (Decimal(str(end_x)), Decimal(str(end_y)))

            g.add_edge(start_key, end_key, data=segment)
        return g
   
    def _translate_2d_to_3d(self) -> List[Dict[str, Any]]:
        """
        Översätter 2D-skissen till 3D-segment genom att traversera en 2D-graf,
        vilket gör processen oberoende av rit-ordningen.
        """
        all_segments = self.parsed_sketch.get("segments", [])
        dimensioned_segments = [s for s in all_segments if s.get("length_dimension") is not None]
        shortcut_segments = [s for s in all_segments if s.get("length_dimension") is None]

        # --- STEG 1: Förstå den sanna topologin ---
        preliminary_graph = self._create_preliminary_2d_graph(dimensioned_segments)
        if not preliminary_graph.nodes:
            return []

        # --- STEG 2: Traversera grafen för att bygga 3D-koordinater ---
        three_d_segments = []
        # Hitta en startpunkt (helst en ändpunkt med grad 1)
        start_node_2d = next((n for n, d in preliminary_graph.degree() if d == 1), list(preliminary_graph.nodes)[0])
        
        # Använd en kö för Breadth-First Search (BFS) traversering
        queue = [(start_node_2d, None)] # (nod, förälder)
        visited = {start_node_2d}
        self.point_2d_to_3d[start_node_2d] = Vec3(0.0, 0.0, 0.0)

        while queue:
            current_node_2d, parent_node_2d = queue.pop(0)
            
            for neighbor_node_2d in preliminary_graph.neighbors(current_node_2d):
                if neighbor_node_2d not in visited:
                    visited.add(neighbor_node_2d)
                    
                    # Hämta segmentdata från kanten
                    segment_data = preliminary_graph.get_edge_data(current_node_2d, neighbor_node_2d)['data']
                    length = segment_data["length_dimension"]
                    
                    # Bestäm riktning baserat på vilken väg vi traverserar
                    start_x = current_node_2d[0]
                    start_y = current_node_2d[1]
                    end_x = neighbor_node_2d[0]
                    end_y = neighbor_node_2d[1]

                    dx = float(end_x - start_x)
                    dy = float(end_y - start_y)
                    angle_rad = math.atan2(dy, dx)
                    angle_deg = math.degrees(angle_rad)
                    direction = self._get_3d_direction_from_angle(angle_deg)
                    
                    # Beräkna 3D-position baserat på föräldern
                    start_3d = self.point_2d_to_3d[current_node_2d]
                    end_3d = start_3d + (direction * length)
                    self.point_2d_to_3d[neighbor_node_2d] = end_3d

                    three_d_segments.append({
                        **segment_data,
                        "start_point_3d": (round(start_3d.x, 6), round(start_3d.y, 6), round(start_3d.z, 6)),
                        "end_point_3d": (round(end_3d.x, 6), round(end_3d.y, 6), round(end_3d.z, 6))
                    })
                    
                    queue.append((neighbor_node_2d, current_node_2d))

        # --- STEG 3: Hantera genvägar (som tidigare) ---
        for segment in shortcut_segments:
            # (Denna logik är oförändrad och bör fungera nu)
            start_2d = segment["start_point"]
            end_2d = segment["end_point"]
            start_x = start_2d['x'] if isinstance(start_2d, dict) else start_2d[0]
            start_y = start_2d['y'] if isinstance(start_2d, dict) else start_2d[1]
            end_x = end_2d['x'] if isinstance(end_2d, dict) else end_2d[0]
            end_y = end_2d['y'] if isinstance(end_2d, dict) else end_2d[1]
            start_key = (Decimal(str(start_x)), Decimal(str(start_y)))
            end_key = (Decimal(str(end_x)), Decimal(str(end_y)))

            if start_key in self.point_2d_to_3d and end_key in self.point_2d_to_3d:
                start_3d = self.point_2d_to_3d[start_key]
                end_3d = self.point_2d_to_3d[end_key]
                three_d_segments.append({
                    **segment,
                    "start_point_3d": (round(start_3d.x, 6), round(start_3d.y, 6), round(start_3d.z, 6)),
                    "end_point_3d": (round(end_3d.x, 6), round(end_3d.y, 6), round(end_3d.z, 6))
                })

        return three_d_segments

    def _build_graph(self, three_d_segments: List[Dict[str, Any]]):
        """
        Bygger en networkx-graf från listan av 3D-segment.
        """
        # Vi behöver en mappning från 3D-koordinat -> nod-ID
        coord_3d_to_node_id: Dict[Tuple[float, float, float], str] = {}

        for segment in three_d_segments:
            start_coord = segment["start_point_3d"]
            end_coord = segment["end_point_3d"]

            for coord in [start_coord, end_coord]:
                if coord not in coord_3d_to_node_id:
                    node = NodeInfo(coords=coord)
                    coord_3d_to_node_id[coord] = node.id
                    self.topology.add_node(node.id, data=node)

            start_node_id = coord_3d_to_node_id[start_coord]
            end_node_id = coord_3d_to_node_id[end_coord]
            
            cleaned_spec_name = segment["spec_name"].strip().replace('-', '_')
            self.topology.add_edge(
                start_node_id, end_node_id,
                segment_id=segment["id"],
                spec_name=cleaned_spec_name,
                is_construction=segment.get("is_construction", False) # Använd .get() för säkerhet
            )


    def _enrich_nodes(self):
        """
        Itererar igenom den färdiga grafen för att klassificera och berika
        varje nod med detaljerad information.
        """
        enriched_nodes_map: Dict[str, NodeInfo] = {}

        for node_id, node_data in self.topology.nodes(data=True):
            base_node = node_data['data']
            degree = self.topology.degree(node_id)
            
            new_node = None
            if degree == 1:
                new_node = EndpointNodeInfo(coords=base_node.coords, id=base_node.id)
                neighbor_id = list(self.topology.neighbors(node_id))[0]
                neighbor_node_data = self.topology.nodes[neighbor_id]['data']
                direction = Vec3(*neighbor_node_data.coords) - Vec3(*new_node.coords)
                new_node.direction = (direction.normalize().x, direction.normalize().y, direction.normalize().z)

            elif degree == 2:
                new_node = BendNodeInfo(coords=base_node.coords, id=base_node.id)
                neighbors = list(self.topology.neighbors(node_id))
                p1_coords = self.topology.nodes[neighbors[0]]['data'].coords
                p2_coords = self.topology.nodes[neighbors[1]]['data'].coords
                p_center = new_node.coords
                
                vec1 = (Vec3(*p1_coords) - Vec3(*p_center)).normalize()
                vec2 = (Vec3(*p2_coords) - Vec3(*p_center)).normalize()
                
                new_node.vectors = [(vec1.x, vec1.y, vec1.z), (vec2.x, vec2.y, vec2.z)]
                
                dot_product = max(-1.0, min(1.0, vec1.dot(vec2)))
                new_node.angle = math.degrees(math.pi - math.acos(dot_product))

            elif degree >= 3:
                new_node = TeeNodeInfo(coords=base_node.coords, id=base_node.id)
                neighbors = list(self.topology.neighbors(node_id))
                neighbor_vectors = [(Vec3(*self.topology.nodes[n_id]['data'].coords) - Vec3(*new_node.coords)).normalize() for n_id in neighbors]
                
                # Hitta de två mest motstående vektorerna (närmast 180 grader)
                best_dot = 1.0
                run_indices = (-1, -1)
                for i in range(len(neighbor_vectors)):
                    for j in range(i + 1, len(neighbor_vectors)):
                        dot_prod = neighbor_vectors[i].dot(neighbor_vectors[j])
                        if dot_prod < best_dot:
                            best_dot = dot_prod
                            run_indices = (i, j)
                
                # Tilldela run och branch baserat på de funna indexen
                if run_indices != (-1, -1):
                    all_indices = set(range(len(neighbors)))
                    branch_index = list(all_indices - set(run_indices))[0]
                    
                    new_node.run_node_ids = [neighbors[run_indices[0]], neighbors[run_indices[1]]]
                    new_node.branch_node_id = neighbors[branch_index]
            
            if new_node:
                spec_names = {data['spec_name'] for _, _, data in self.topology.edges(node_id, data=True)}
                if len(spec_names) > 1: new_node.requires_reducer = True
                
                # Tilldela primär specifikation
                if spec_names:
                    # En mer robust metod skulle vara att sortera eller välja baserat på en regel
                    first_spec_name = list(spec_names)[0]
                    new_node.assigned_spec = self.catalog.get_spec(first_spec_name)

                enriched_nodes_map[node_id] = new_node
                self.topology.nodes[node_id]['data'] = new_node

        self.nodes = list(enriched_nodes_map.values())

    def _cleanup_graph(self):
        """Tar bort konstruktionslinjer och isolerade noder från grafen."""
        # Hitta och ta bort konstruktionskanter
        construction_edges = [
            (u, v) for u, v, data in self.topology.edges(data=True)
            if data.get("is_construction")
        ]
        self.topology.remove_edges_from(construction_edges)
        print(f"  -> Rensning: {len(construction_edges)} konstruktionskanter borttagna.")

        # Hitta och ta bort isolerade noder (noder utan kanter)
        isolated_nodes = [
            node_id for node_id, degree in self.topology.degree() if degree == 0
        ]
        self.topology.remove_nodes_from(isolated_nodes)
        print(f"  -> Rensning: {len(isolated_nodes)} isolerade noder borttagna.")