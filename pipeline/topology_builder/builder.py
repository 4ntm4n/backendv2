# pipeline/2_topology_builder/builder.py

import math
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
        self.coord_to_node_id: Dict[Tuple[float, float, float], str] = {}


    def build(self) -> Tuple[List[NodeInfo], nx.Graph]:
        """Huvudmetod som kör hela byggprocessen."""
        print("--- Modul 2 (Topology Builder): Startar ---")

        three_d_segments = self._translate_2d_to_3d()
        print(f"  -> Steg 1: {len(three_d_segments)} 3D-segment skapade.")

        self._build_graph(three_d_segments)
        print(f"  -> Steg 2: Graf skapad med {self.topology.number_of_nodes()} noder och {self.topology.number_of_edges()} kanter.")

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
            30.0:  Vec3(-1.0, 0.0, 0.0),   # +y (Grön) = Korrekt
            90.0:  Vec3(0.0, 0.0, -1.0),   # +Z (Blå) = Korrekt
            150.0: Vec3(0.0, 1.0, 0.0),  # -X (Röd) = Korrekt
            210.0: Vec3(1.0, 0.0, 0.0),  # -Y (Grön) = Korrekt
            270.0: Vec3(0.0, 0.0, 1.0),  # -Z (Blå) = Korrekt
            330.0: Vec3(0.0, -1.0, 0.0)    # +X (Röd) = Korrekt
        }


        def angle_distance(a1, a2):
            phi = abs(a2 - a1) % 360
            return min(phi, 360 - phi)
        closest_angle = min(standard_directions.keys(), key=lambda std_angle: angle_distance(std_angle, angle_deg))
        snapped_direction = standard_directions[closest_angle]
        if not math.isclose(closest_angle, angle_deg, abs_tol=1.0):
            print(f"    -> INFO: Vinkel {angle_deg:.1f}° tolkad som närmsta standardvinkel {closest_angle}°.")
        return snapped_direction

    def _translate_2d_to_3d(self) -> List[Dict[str, Any]]:
        """
        Använder "3D-penna"-logiken för att omvandla 2D-skissen till en lista
        av 3D-segment.
        """
        three_d_segments = []
        current_3d_point = Vec3(0.0, 0.0, 0.0)
        point_map: Dict[Tuple[float, float], Vec3] = {}

        for segment in self.parsed_sketch.get("segments", []):
            start_2d = segment["start_point"]
            end_2d = segment["end_point"]
            length = segment.get("length_dimension")

            if start_2d not in point_map:
                point_map[start_2d] = current_3d_point
            
            start_3d = point_map[start_2d]
            
            if length is None:
                print(f"    -> VARNING: Segment {segment['id']} saknar längd-dimension. Hoppar över.")
                continue

            dx = end_2d[0] - start_2d[0]
            dy = end_2d[1] - start_2d[1]
            angle_rad = math.atan2(dy, dx)
            angle_deg = math.degrees(angle_rad)
            direction = self._get_3d_direction_from_angle(angle_deg)

            end_3d = start_3d + (direction * length)

            point_map[end_2d] = end_3d
            current_3d_point = end_3d

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
        for segment in three_d_segments:
            start_coord = segment["start_point_3d"]
            end_coord = segment["end_point_3d"]

            for coord in [start_coord, end_coord]:
                if coord not in self.coord_to_node_id:
                    node = NodeInfo(coords=coord)
                    self.coord_to_node_id[coord] = node.id
                    self.topology.add_node(node.id, data=node)

            start_node_id = self.coord_to_node_id[start_coord]
            end_node_id = self.coord_to_node_id[end_coord]
            
            cleaned_spec_name = segment["spec_name"].strip().replace('-', '_')
            self.topology.add_edge(
                start_node_id, end_node_id,
                segment_id=segment["id"],
                spec_name=cleaned_spec_name,
                is_construction=segment["is_construction"]
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
