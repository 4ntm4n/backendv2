# Spara denna kod i: backendv2/geometry_executor/executor.py

import math
from typing import Dict, Any, List, Tuple, Optional

# Importera FreeCAD-typer. Dessa kommer att vara riktiga moduler
# när koden körs i FreeCAD-miljön.
import Part
from FreeCAD import Vector

# Importera från andra V2-moduler med absoluta sökvägar
from components_catalog.loader import CatalogLoader
from topology_builder.node_types_v2 import NodeInfo, BendNodeInfo, TeeNodeInfo
from shared.types import BuildPlanItem

class GeometryExecutor:
    """
    Tar en slutgiltig, justerad byggplan och skapar en 3D-modell i FreeCAD.
    """
    def __init__(self, final_plans: List[List[BuildPlanItem]], nodes: List[NodeInfo], catalog: CatalogLoader):
        self.plans = final_plans
        self.nodes_by_id = {node.id: node for node in nodes}
        self.catalog = catalog
        self.solid_bodies: List[Part.Shape] = []
        self.centerline_wires: List[Part.Wire] = []

    def build_model(self) -> Part.Shape:
        """
        Huvudmetod som kör hela byggprocessen.
        FÖR UTVECKLING: Returnerar den första centrumlinjen som ett Part.Wire för visuell inspektion.
        """
        print("--- Geometry Executor: Startar 3D-modellbygge ---")

        # Steg 1: Bygg alla centrumlinjer
        self._build_centerlines()

        # Steg 2 & 3 är tillfälligt avstängda under utveckling för att vi ska kunna se centrumlinjen.
        # self._create_solid_bodies()
        # final_model = self._fuse_solids()
        
        # För nu, returnera den första centrumlinjen vi skapade för att kunna inspektera den.
        if self.centerline_wires:
            print("--- Geometry Executor: Klar. Returnerar centrumlinje för inspektion. ---")
            return self.centerline_wires[0]
        
        print("--- Geometry Executor: Klar. Inga centrumlinjer skapades. ---")
        return Part.Shape()

    def _build_centerlines(self):
        """Loopar igenom self.plans och skapar en Part.Wire för varje."""
        print("  -> Steg 1: Bygger centrumlinjer...")
        for plan in self.plans:
            wire = self._build_single_centerline(plan)
            if wire:
                self.centerline_wires.append(wire)
        print(f"     -> {len(self.centerline_wires)} centrumlinje(r) skapade.")

    def _build_single_centerline(self, plan: List[BuildPlanItem]) -> Optional[Part.Wire]:
        """Bygger en enskild, kontinuerlig centrumlinje från en byggplan med "3D-penna"-logik."""
        print(f"     -> Bygger enskild centrumlinje med {len(plan)} steg...")
        centerline_edges: List[Part.Edge] = []
        
        if not plan or not plan[0].get('node_id'):
            return None

        # Initiera "pennan"
        start_node = self.nodes_by_id.get(plan[0]['node_id'])
        if not start_node: return None
        
        current_pos = Vector(*start_node.coords)
        # Hitta startriktning (detta behöver finslipas i analys-fasen)
        # För nu antar vi att EndpointNode har en 'direction'-vektor.
        current_dir = getattr(start_node, 'direction', Vector(1,0,0))

        # Iterera och bygg kanterna
        for item in plan:
            item_type = item.get('type')
            if item_type == 'STRAIGHT':
                length = item.get('length') or 0.0
                if length > 1e-6:
                    end_point = current_pos + current_dir * length
                    line_edge = Part.makeLine(current_pos, end_point)
                    centerline_edges.append(line_edge)
                    current_pos = end_point
            
            elif item_type == 'COMPONENT':
                node = self.nodes_by_id.get(item['node_id'])
                if isinstance(node, BendNodeInfo):
                    # Här skulle logiken för att skapa böjens båge och tangenter ligga
                    # och uppdatera current_pos och current_dir.
                    # print(f"        (TODO: Skapa böj vid {node.id})")
                    pass
                elif isinstance(node, TeeNodeInfo):
                    # Här skulle logiken för att skapa T-rörets huvudlopp ligga.
                    # print(f"        (TODO: Skapa T-rör vid {node.id})")
                    pass
        
        if centerline_edges:
            return Part.Wire(centerline_edges)
        return None

    def _create_solid_bodies(self):
        """PLATSHÅLLARE: Loopar igenom planer och centrumlinjer för att skapa solider."""
        print("  -> Steg 2: Skapar solida 3D-kroppar... (AVSTÄNGD)")
        pass

    def _fuse_solids(self) -> Part.Shape:
        """PLATSHÅLLARE: Använder Part.MultiFuse för att slå ihop self.solid_bodies."""
        print("  -> Steg 3: Fogar samman solider... (AVSTÄNGD)")
        return Part.Shape()
