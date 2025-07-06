import math
import copy
from typing import Dict, Any, List, Tuple

import networkx as nx

# Importera våra egna typer och klasser
from components_catalog.loader import CatalogLoader, ComponentData
from pipeline.topology_builder.node_types_v2 import NodeInfo, BendNodeInfo, TeeNodeInfo, EndpointNodeInfo
from pipeline.shared.types import BuildPlan, BuildPlanItem

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

    def _adjust_segment(self, segment: List[BuildPlanItem]) -> List[BuildPlanItem]:
        """Justerar ett enskilt segment av en byggplan."""
        
        # TODO: Steg A: Beräkna den totala geometriska längden av segmentet.
        # Detta görs genom att följa noderna i topologin och summera avstånden
        # mellan dem med hjälp av deras 3D-koordinater.
        geometric_distance = 0.0

        # TODO: Steg B: Beräkna den totala "bygglängden" för alla fasta komponenter.
        # Loopa igenom komponenterna i segmentet (böjar, konor etc.) och summera deras
        # fasta längder (t.ex. bend.center_to_end, reducer.length).
        component_build_length = 0.0

        # TODO: Steg C: Beräkna diskrepans.
        discrepancy = geometric_distance - component_build_length
        
        # TODO: Steg D: Agera baserat på diskrepansen.
        straight_pipes = [item for item in segment if item['type'] == 'STRAIGHT']
        
        if discrepancy >= 0:
            # "Happy Path": Fördela överskottet på de raka rören.
            if straight_pipes:
                length_per_pipe = discrepancy / len(straight_pipes)
                for pipe in straight_pipes:
                    pipe['length'] = length_per_pipe
        else:
            # "Shortfall Path": Vi har ett underskott.
            shortfall = -discrepancy
            
            # Sätt alla raka rör till längd 0
            for pipe in straight_pipes:
                pipe['length'] = 0.0

            # Identifiera alla kapbara komponenter i segmentet
            cappable_components = [] # TODO: Fyll denna lista
            
            # Anropa den smarta kapnings-logiken
            self._handle_shortfall(cappable_components, shortfall)
            
        return segment

    def _handle_shortfall(self, components: List[ComponentData], shortfall: float):
        """
        Innehåller den hierarkiska logiken för att hantera ett underskott.
        """
        print(f"    -> Hanterar underskott på {shortfall:.2f} mm...")
        
        # TODO: Steg 1: "Den Gyllene Lösningen" (Ett Enda Kap)
        # Loopa igenom komponenterna. Om en enskild komponent kan absorbera
        # hela underskottet själv, applicera kapningen och returnera.
        
        # TODO: Steg 2: "Komfort-kapning" (Proportionerlig fördelning)
        # Beräkna totalt "komfort-spelrum" för alla komponenter.
        # Om det räcker för att täcka underskottet, fördela kapningen
        # proportionerligt och returnera.

        # TODO: Steg 3: "Nödvändighets-kapning"
        # Om underskottet kvarstår, kapa först ner allt till `preferred_min_tangent`.
        # Fördela sedan det återstående underskottet proportionerligt ner
        # mot `physical_min_tangent`.

        # TODO: Steg 4: Omöjligt Bygge
        # Om underskottet fortfarande är > 0 efter Steg 3, kasta ett fel.
        # raise ImpossibleBuildError(f"Kunde inte lösa underskott på {shortfall:.2f} mm.")

        pass # Ta bort när implementationen är klar