# pipeline/topology_builder/builder.py

import math
from typing import Dict, Any, List, Tuple
import networkx as nx

# Importera från andra V2-moduler
from components_catalog.loader import CatalogLoader
from .node_types_v2 import NodeInfo, BendNodeInfo, TeeNodeInfo, EndpointNodeInfo

class TopologyBuilder:
    """
    Bygger en intelligent, berikad 3D-topologi från ren skissdata.
    """
    def __init__(self, parsed_sketch: Dict[str, Any], catalog: CatalogLoader):
        self.parsed_sketch = parsed_sketch
        self.catalog = catalog
        self.topology = nx.Graph()
        self.nodes: List[NodeInfo] = []
        # Hjälp-dictionary för att mappa 3D-koordinater till nod-ID i grafen
        self.coord_to_node_id: Dict[Tuple[float, float, float], str] = {}


    def build(self) -> Tuple[List[NodeInfo], nx.Graph]:
        """Huvudmetod som kör hela byggprocessen."""
        print("--- Modul 2 (Topology Builder): Startar ---")

        # Steg 1: Översätt 2D-skiss till 3D-segment
        three_d_segments = self._translate_2d_to_3d()
        print(f"  -> Steg 1: {len(three_d_segments)} 3D-segment skapade.")

        # Steg 2: Bygg och berika grafen
        self._build_graph(three_d_segments)
        print(f"  -> Steg 2: Graf skapad med {self.topology.number_of_nodes()} noder och {self.topology.number_of_edges()} kanter.")

        # Steg 3 & 4: Klassificera och validera noder
        self._enrich_nodes()
        print(f"  -> Steg 3 & 4: Noder klassificerade och berikade.")
        
        print("--- Topology Builder: Klar ---")
        return self.nodes, self.topology

    def _get_3d_direction_from_angle(self, angle_deg: float) -> Tuple[float, float, float]:
        """
        Omvandlar en 2D-isometrisk vinkel till en normaliserad 3D-riktningsvektor
        genom att "snappa" den till närmsta av de 6 standardvinklarna.
        """
        angle_deg = angle_deg % 360
        standard_directions = {
            30.0:  (1.0, 0.0, 0.0),    # +X
            90.0:  (0.0, 0.0, -1.0),   # -Z
            150.0: (0.0, -1.0, 0.0),   # -Y
            210.0: (-1.0, 0.0, 0.0),   # -X
            270.0: (0.0, 0.0, 1.0),    # +Z
            330.0: (0.0, 1.0, 0.0)     # +Y
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
        current_3d_point = (0.0, 0.0, 0.0)
        point_map: Dict[Tuple[float, float], Tuple[float, float, float]] = {}

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

            end_3d = tuple(round(s + d * length, 6) for s, d in zip(start_3d, direction))

            point_map[end_2d] = end_3d
            current_3d_point = end_3d

            three_d_segments.append({**segment, "start_point_3d": start_3d, "end_point_3d": end_3d})
        return three_d_segments

    def _build_graph(self, three_d_segments: List[Dict[str, Any]]):
        """
        Bygger en networkx-graf från listan av 3D-segment.
        Varje kant berikas med metadata från skissen.
        """
        for segment in three_d_segments:
            start_coord = segment["start_point_3d"]
            end_coord = segment["end_point_3d"]

            # Lägg till noder om de inte redan finns
            for coord in [start_coord, end_coord]:
                if coord not in self.coord_to_node_id:
                    # Skapa en grundläggande NodeInfo för nu. Den kommer att
                    # uppgraderas till rätt typ i _enrich_nodes.
                    node = NodeInfo(coords=coord)
                    # --- LÄGG TILL DENNA RAD ---
                    node.vertex_coord_vec = lambda: Vector(*node.coords)
                    # --- SLUT PÅ TILLÄGG ---
                    self.coord_to_node_id[coord] = node.id
                    self.topology.add_node(node.id, data=node)

                    if coord not in self.coord_to_node_id:
                    

            # Hämta nod-IDn
            start_node_id = self.coord_to_node_id[start_coord]
            end_node_id = self.coord_to_node_id[end_coord]


            # Lägg till kanten och berika den med all relevant metadata
            self.topology.add_edge(
                start_node_id,
                end_node_id,
                segment_id=segment["id"],
                pipe_spec=segment["pipe_spec"].strip().replace('-', '_'),
                is_construction=segment["is_construction"]
            )

    def _enrich_nodes(self):
        """
        Itererar igenom den färdiga grafen för att klassificera och berika
        varje nod med detaljerad information.
        """
        enriched_nodes_map: Dict[str, NodeInfo] = {}
        nodes_to_remove = []

        # --- Pass A: Lös specialvinkel-kedjor (om vi implementerar det) ---
        # self._simplify_construction_chains() # Detta anropas först

        for node_id, node_data in self.topology.nodes(data=True):
            base_node = node_data['data']
            
            # Använd enbart kanter som inte är bygghjälpslinjer för att bestämma graden
            real_edges = [e for e in self.topology.edges(node_id, data=True) if not e[2].get('is_construction')]
            degree = len(real_edges)
            
            new_node = None
            if degree == 1:
                new_node = EndpointNodeInfo(coords=base_node.coords, id=base_node.id)
                # Hämta den utgående vektorn
                neighbor_id = list(self.topology.neighbors(node_id))[0]
                neighbor_node = self.topology.nodes[neighbor_id]['data']
                direction = tuple(c_n - c_start for c_n, c_start in zip(neighbor_node.coords, new_node.coords))
                len_dir = math.sqrt(sum(c*c for c in direction))
                new_node.direction = tuple(c / len_dir for c in direction)

            elif degree == 2:
                new_node = BendNodeInfo(coords=base_node.coords, id=base_node.id)
                neighbors = list(self.topology.neighbors(node_id))
                p_center_vec = new_node.vertex_coord_vec()

                # Beräkna inkommande/utgående vektorer för böjen
                n1 = self.topology.nodes[neighbors[0]]['data']
                n2 = self.topology.nodes[neighbors[1]]['data']
                vec1 = (n1.vertex_coord_vec() - p_center_vec).normalize()
                vec2 = (n2.vertex_coord_vec() - p_center_vec).normalize()
                new_node.vectors = [vec1.toTuple(), vec2.toTuple()]

                # Beräkna vinkel
                dot_product = max(-1.0, min(1.0, vec1.dot(vec2)))
                new_node.external_angle_rad = math.acos(dot_product)
                new_node.angle_rad = math.pi - new_node.external_angle_rad
                new_node.angle = math.degrees(new_node.angle_rad)

            elif degree >= 3:
                new_node = TeeNodeInfo(coords=base_node.coords, id=base_node.id)
                neighbors = list(self.topology.neighbors(node_id))
                neighbor_vectors = [(self.topology.nodes[n_id]['data'].vertex_coord_vec() - new_node.vertex_coord_vec()).normalize() for n_id in neighbors]
                
                # Hitta de två mest motstående vektorerna (närmast 180 grader)
                best_dot = 1.0
                run_indices = (-1, -1)
                for i in range(len(neighbor_vectors)):
                    for j in range(i + 1, len(neighbor_vectors)):
                        dot_prod = neighbor_vectors[i].dot(neighbor_vectors[j])
                        if dot_prod < best_dot:
                            best_dot = dot_prod
                            run_indices = (i, j)

                # Tilldela run och branch
                run_node_ids = [neighbors[run_indices[0]], neighbors[run_indices[1]]]
                branch_node_id = next(n_id for n_id in neighbors if n_id not in run_node_ids)
                new_node.run_node_ids = run_node_ids
                new_node.branch_node_id = branch_node_id
            
            else: # degree == 0
                new_node = base_node # Behåll som UNKNOWN
            
            if new_node:
                # Sätt primär specifikation och kolla om kona behövs
                pipe_specs = {data['pipe_spec'] for _, _, data in real_edges}
                if pipe_specs:
                    first_edge_spec = list(pipe_specs)[0]
                    new_node.assigned_spec = self.catalog.get_spec(first_edge_spec)
                if len(pipe_specs) > 1:
                    new_node.requires_reducer = True

                enriched_nodes_map[node_id] = new_node
                self.topology.nodes[node_id]['data'] = new_node

        self.nodes = list(enriched_nodes_map.values())