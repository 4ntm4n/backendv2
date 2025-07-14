# main_runner.py


# =================================================================
# === HOT-RELOADER FÖR UTVECKLING =================================
# =================================================================
# Denna kodsnutt säkerställer att alla våra projekt-moduler
# laddas om från fil varje gång makrot körs. Detta låter oss
# ändra i koden och se resultaten direkt utan att starta om FreeCAD.
import os, sys
import importlib

# Lista med namnen på ALLA moduler i vårt projekt som vi kan tänkas redigera.
# Python använder punkt-notation för paket.
modules_to_reload = [
    "main_runner",
    "pipeline.shared.types",
    "pipeline.sketch_parser.parser",
    "pipeline.topology_builder.node_types_v2",
    "pipeline.planner.planner",
    "pipeline.topology_builder.builder",
    "pipeline.centerline_builder.builder",
    "pipeline.plan_adjuster.adjuster",
    "pipeline.geometry_executor.executor",
    "components_catalog.loader"
]

print("--- Hot-reloader: Laddar om projekt-moduler... ---")
for module_name in modules_to_reload:
    # Vi kollar om modulen redan finns i cachen innan vi försöker ladda om den.
    if module_name in sys.modules:
        try:
            importlib.reload(sys.modules[module_name])
            # print(f"  -> Laddade om: {module_name}")
        except Exception as e:
            print(f"  -> FEL vid omladdning av {module_name}: {e}")

print("--- Omladdning klar. Startar huvudskript. ---")
# =================================================================

from typing import List, Dict, Any

# Försök importera FreeCAD-bibliotek.
# Detta gör att filen inte kraschar om den analyseras utanför FreeCAD.
try:
    from FreeCAD import Part, Vector
    FREECAD_AVAILABLE = True
    print("INFO: FreeCAD-biblioteket importerades korrekt. 3D-generering bör fungera")
except ImportError:
    print("VARNING: FreeCAD-bibliotek kunde inte importeras. 3D-generering kommer inte fungera.")
    Part = None
    Vector = None
    FREECAD_AVAILABLE = False

# Importera alla våra pipeline-moduler
from components_catalog.loader import CatalogLoader
from pipeline.sketch_parser.parser import SketchParser
from pipeline.topology_builder.builder import TopologyBuilder
from pipeline.planner.planner import Planner
from pipeline.centerline_builder.builder import CenterlineBuilder
from pipeline.plan_adjuster.adjuster import PlanAdjuster, ImpossibleBuildError
from pipeline.geometry_executor.executor import GeometryExecutor




def process_sketch_to_shape(proto_data: bytes) -> 'Part.Shape':
    """
    Huvudfunktion som kör hela pipeline, från rådata till färdig 3D-modell.
    """
    try:
        # --- Steg 0, 1, 2 (oförändrade) ---
        project_root = os.path.dirname(os.path.abspath(__file__))
        catalog_path = os.path.join(project_root, "components_catalog")
        catalog = CatalogLoader(catalog_path)
        
        parser = SketchParser()
        parsed_sketch = parser.parse(proto_data)

        builder = TopologyBuilder(parsed_sketch, catalog)
        nodes, graph = builder.build()

        # === NY, KORREKT KEDJA ===

        # STEG 3: Skapa logiska resplaner
        planner = Planner(nodes=nodes, topology=graph, catalog=catalog)
        travel_plans = planner.create_plans()

        # STEG 4: Skapa instans av Adjuster (för dependency injection)
        # Den skapas här men kommer bara att användas inuti CenterlineBuilder vid behov.
        adjuster = PlanAdjuster(
            semantic_plans=travel_plans, 
            nodes=nodes, 
            topology=graph, 
            catalog=catalog
        )
        # STEG 5: Bygg den detaljerade geometriska planen
        centerline_builder = CenterlineBuilder(
            travel_plans=travel_plans,
            nodes=nodes,
            topology=graph,  # Lägg till topologin
            catalog=catalog, # Lägg till katalogen
            adjuster=adjuster  # Lägg till adjustern
        )

        final_drawing_plans = centerline_builder.build_drawing_plans()

        # STEG 7: Exekvera och rita modellen (Återställd till den gamla, fungerande logiken)
        all_wires = []
        # Loopa igenom varje plan som vår nya kedja har producerat
        for plan in final_drawing_plans:
            if not plan:
                continue

            # Skapa en Executor för varje enskild plan, precis som förut
            executor = GeometryExecutor(
                explicit_plan=plan, # Använd det korrekta argumentnamnet
                freecad_part_module=Part,
                freecad_vector_class=Vector
            )
            wire = executor.build_model()
            if wire:
                all_wires.append(wire)

        # Foga samman alla trådar till ett enda objekt för visualisering
        final_model = Part.Compound(all_wires) if all_wires else None

        print("===================================")
        print("=== Pipeline slutförd framgångsrikt ===")
        print("===================================")
        
        return final_model

    except ImpossibleBuildError as e:
        print("\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print(f"FEL: Bygget är geometriskt omöjligt.")
        print(f"Anledning: {e}")
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n")
        return None
    except Exception as e:
        print(f"\nEtt oväntat fel inträffade i pipelinen: {e}")
        import traceback
        traceback.print_exc()
        return None