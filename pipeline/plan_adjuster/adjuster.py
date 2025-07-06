import math
import copy
from typing import Dict, Any, List, Tuple
from dataclasses import dataclass

import networkx as nx

# Importera våra egna typer och klasser
from components_catalog.loader import CatalogLoader, ComponentData
from pipeline.topology_builder.node_types_v2 import NodeInfo, BendNodeInfo, TeeNodeInfo, EndpointNodeInfo
from pipeline.shared.types import BuildPlan, BuildPlanItem

from components_catalog.loader import Bend90Data, ReducerData


class ImpossibleBuildError(Exception):
    """Ett anpassat fel som kastas när en design är geometriskt omöjlig."""
    pass

class PlanAdjuster:
    """
    Justerar längder i byggplaner med en avancerad, prioriterad ART-algoritm.
    """
    def __init__(self, plans: List[BuildPlan], nodes: List[NodeInfo], topology: nx.Graph, catalog: CatalogLoader):
        self.raw_plans = plans
        self.nodes_by_id = {node.id: node for node in nodes}
        self.topology = topology
        self.catalog = catalog
        self.adjusted_plans = copy.deepcopy(plans)

    def adjust_plans(self) -> List[BuildPlan]:
        """Huvudmetod som justerar alla byggplaner."""
        print("--- Modul 4 (PlanAdjuster): Startar justering ---")
        
        for i, plan in enumerate(self.adjusted_plans):
            print(f"  -> Justerar plan {i+1}...")
            self.adjusted_plans[i] = self._find_and_adjust_segments_in_plan(plan)
            
        print("--- PlanAdjuster: Klar. ---")
        return self.adjusted_plans

    def _find_and_adjust_segments_in_plan(self, plan: BuildPlan) -> BuildPlan:
        """
        Går igenom en byggplan och identifierar justerbara segment.
        Ett segment är en kedja av komponenter mellan två "fasta" noder.
        """
        # TODO: Implementera logik för att identifiera segment.
        # En enkel start är att behandla hela planen som ett enda segment
        # om den går mellan två EndpointNodeInfo.
        
        # För nu, låt oss anta att hela planen är ett segment.
        segment_items = plan # Förenkling
        
        adjusted_segment = self._adjust_segment(segment_items)
        
        return adjusted_segment

    def _get_node_coords(self, node_id: str) -> Tuple[float, float, float]:
        """Hjälpmetod för att säkert hämta en nods koordinater."""
        return self.nodes_by_id[node_id].coords


    def _adjust_segment(self, segment: List[BuildPlanItem]) -> List[BuildPlanItem]:
        """Justerar ett enskilt segment av en byggplan."""
        
        # --- Steg A: Beräkna den totala geometriska längden ---
        # Extrahera en ren lista av nod-ID:n från segmentet
        node_ids_in_path = [item['node_id'] for item in segment if item.get('node_id')]
        
        geometric_distance = 0.0
        # Summera avståndet mellan varje par av på varandra följande noder
        for i in range(len(node_ids_in_path) - 1):
            p1 = self._get_node_coords(node_ids_in_path[i])
            p2 = self._get_node_coords(node_ids_in_path[i+1])
            geometric_distance += math.dist(p1, p2)

        # --- Steg B: Beräkna den totala "bygglängden" för alla fasta komponenter ---
        component_build_length = 0.0
        # Hämta alla komponenter som inte är ändpunkter
        component_items = [item for item in segment if item['type'] == 'COMPONENT' and item['component_name'] != 'ENDPOINT']
        
        for item in component_items:
            spec = self.catalog.get_spec(item['spec_name'])
            # Hoppa över om spec eller komponent inte hittas
            if not spec or not spec.components.get(item['component_name']):
                continue
            
            component_obj = spec.components.get(item['component_name'])
            
            # Här lägger vi till logik för varje komponenttyp
            if isinstance(component_obj, Bend90Data):
                # En 90-graders böj i ett U-format rör bidrar med sitt CTE-mått på båda sidor
                component_build_length += component_obj.center_to_end * 2
            # TODO: Lägg till elif för ReducerData, ClampData etc. här
            # elif isinstance(component_obj, ReducerData):
            #     component_build_length += component_obj.length
            
        # --- Steg C: Beräkna diskrepans ---
        discrepancy = geometric_distance - component_build_length
        
        # --- Steg D: Agera baserat på diskrepansen ---
        straight_pipes = [item for item in segment if item['type'] == 'STRAIGHT']
        
        if discrepancy >= 0:
            # "Happy Path"
            if straight_pipes:
                length_per_pipe = discrepancy / len(straight_pipes)
                for pipe in straight_pipes:
                    pipe['length'] = length_per_pipe
        else:
            # "Shortfall Path"
            shortfall = -discrepancy
            for pipe in straight_pipes:
                pipe['length'] = 0.0
            
            # Enkel logik för att klara test 2: fördela lika
            # Detta kommer vi att ersätta med _handle_shortfall() senare
            if component_items:
                cut_per_tangent = shortfall / (len(component_items) * 2) # Antar 2 tangenter per komponent
                for item in component_items:
                    item['cut_tangent_start'] = cut_per_tangent
                    item['cut_tangent_end'] = cut_per_tangent
                    
        return segment

    # I pipeline/plan_adjuster/adjuster.py

class PlanAdjuster:
    """
    Justerar längder i byggplaner med en avancerad, prioriterad ART-algoritm.
    """
    def __init__(self, plans: List[BuildPlan], nodes: List[NodeInfo], topology: nx.Graph, catalog: CatalogLoader):
        self.raw_plans = plans
        self.nodes_by_id = {node.id: node for node in nodes}
        self.topology = topology
        self.catalog = catalog
        self.adjusted_plans = copy.deepcopy(plans)

    def adjust_plans(self) -> List[BuildPlan]:
        """Huvudmetod som justerar alla byggplaner."""
        print("--- Modul 4 (PlanAdjuster): Startar justering ---")
        
        for i, plan in enumerate(self.adjusted_plans):
            print(f"  -> Justerar plan {i+1}...")
            self.adjusted_plans[i] = self._find_and_adjust_segments_in_plan(plan)
            
        print("--- PlanAdjuster: Klar. ---")
        return self.adjusted_plans

    def _find_and_adjust_segments_in_plan(self, plan: BuildPlan) -> BuildPlan:
        """Går igenom en byggplan och identifierar justerbara segment."""
        # Förenkling: Behandla hela planen som ett enda segment.
        # Detta fungerar för våra nuvarande tester.
        adjusted_segment = self._adjust_segment(plan)
        return adjusted_segment

    def _get_node_coords(self, node_id: str) -> Tuple[float, float, float]:
        """Hjälpmetod för att säkert hämta en nods koordinater."""
        return self.nodes_by_id[node_id].coords

    def _adjust_segment(self, segment: List[BuildPlanItem]) -> List[BuildPlanItem]:
        """Justerar ett enskilt segment av en byggplan."""
        node_ids_in_path = [item['node_id'] for item in segment if item.get('node_id')]
        
        geometric_distance = sum(
            math.dist(self._get_node_coords(node_ids_in_path[i]), self._get_node_coords(node_ids_in_path[i+1]))
            for i in range(len(node_ids_in_path) - 1)
        )

        component_items = [item for item in segment if item['type'] == 'COMPONENT' and item.get('component_name') != 'ENDPOINT']
        component_build_length = 0.0
        for item in component_items:
            spec = self.catalog.get_spec(item['spec_name'])
            if not spec: continue
            
            component_obj = spec.components.get(item['component_name'])
            if not component_obj: continue
            
            if hasattr(component_obj, 'center_to_end'): # För böjar
                component_build_length += component_obj.center_to_end * 2 # Antagande för U-form
            elif hasattr(component_obj, 'length'): # För konor
                component_build_length += component_obj.length
            # TODO: Lägg till logik för andra komponenttyper med fasta mått

        discrepancy = geometric_distance - component_build_length
        straight_pipes = [item for item in segment if item['type'] == 'STRAIGHT']
        
        if discrepancy >= 0:
            if straight_pipes:
                length_per_pipe = discrepancy / len(straight_pipes)
                for pipe in straight_pipes:
                    pipe['length'] = length_per_pipe
        else:
            shortfall = -discrepancy
            for pipe in straight_pipes:
                pipe['length'] = 0.0
            
            self._handle_shortfall(component_items, shortfall)
            
        return segment

    
    def _handle_shortfall(self, component_items: List[BuildPlanItem], shortfall: float):
        """Innehåller den hierarkiska logiken för att hantera ett underskott."""
        print(f"    -> Hanterar underskott på {shortfall:.2f} mm...")
        
        # Steg 0: Förbered en lista med alla kapbara tangenter. En böj har två, en clamp har en.
        @dataclass
        class CappableTangent:
            item: BuildPlanItem
            tangent_key: str # 'cut_tangent_start' eller 'cut_tangent_end'
            obj: ComponentData

        cappable_tangents: List[CappableTangent] = []
        for item in component_items:
            spec = self.catalog.get_spec(item['spec_name'])
            if not spec: continue
            comp_obj = spec.components.get(item['component_name'])

            if hasattr(comp_obj, 'tangent'): # Allmän kontroll för kapbarhet
                # För nu antar vi att både start- och end-tangenter är kapbara om de finns
                cappable_tangents.append(CappableTangent(item, 'cut_tangent_start', comp_obj))
                cappable_tangents.append(CappableTangent(item, 'cut_tangent_end', comp_obj))

        if not cappable_tangents:
            raise ImpossibleBuildError(f"Underskott på {shortfall:.2f}mm, inga kapbara komponenter.")

        # Steg 1: "Den Gyllene Lösningen" - TODO

        # Steg 2: "Komfort-kapning"
        comfort_leeway_map = {
            i: (t.obj.tangent - t.obj.preferred_min_tangent)
            for i, t in enumerate(cappable_tangents)
            if (t.obj.tangent - t.obj.preferred_min_tangent) > 1e-6
        }
        total_comfort_leeway = sum(comfort_leeway_map.values())

        if shortfall <= total_comfort_leeway:
            print("    -> Löser med 'Komfort-kapning'.")
            for i, leeway in comfort_leeway_map.items():
                proportion = leeway / total_comfort_leeway
                cut_amount = shortfall * proportion
                tangent_to_cut = cappable_tangents[i]
                tangent_to_cut.item[tangent_to_cut.tangent_key] = cut_amount
            return

        # Steg 3: "Nödvändighets-kapning"
        print("    -> Komfort-kapning räckte inte. Fortsätter med 'Nödvändighets-kapning'.")
        # Kapa först ner allt till komfortgränsen
        for i, leeway in comfort_leeway_map.items():
            tangent_to_cut = cappable_tangents[i]
            tangent_to_cut.item[tangent_to_cut.tangent_key] = leeway
        
        remaining_shortfall = shortfall - total_comfort_leeway
        
        # Beräkna återstående fysiskt spelrum
        physical_leeway_map = {
            i: (t.obj.preferred_min_tangent - t.obj.physical_min_tangent)
            for i, t in enumerate(cappable_tangents)
            if (t.obj.preferred_min_tangent - t.obj.physical_min_tangent) > 1e-6
        }
        total_physical_leeway = sum(physical_leeway_map.values())
        
        if remaining_shortfall <= total_physical_leeway:
            for i, leeway in physical_leeway_map.items():
                proportion = leeway / total_physical_leeway if total_physical_leeway > 0 else 0
                additional_cut = remaining_shortfall * proportion
                tangent_to_cut = cappable_tangents[i]
                tangent_to_cut.item[tangent_to_cut.tangent_key] += additional_cut
            return

        # Steg 4: Omöjligt Bygge
        raise ImpossibleBuildError(f"Kunde inte lösa underskott på {shortfall:.2f} mm. För lite material att kapa.")