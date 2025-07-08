# main_runner.py

import os, sys
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
from pipeline.build_planner.planner import BuildPlanner
from pipeline.plan_adjuster.adjuster import PlanAdjuster, ImpossibleBuildError
from pipeline.geometry_executor.executor import GeometryExecutor

# Ladda om alla våra moduler för att säkerställa att de senaste ändringarna används
# Detta är mycket användbart när man utvecklar ett makro i FreeCAD.
from importlib import reload
reload(sys.modules['components_catalog.loader'])
reload(sys.modules['pipeline.sketch_parser.parser'])
reload(sys.modules['pipeline.topology_builder.builder']) 
reload(sys.modules['pipeline.build_planner.planner'])
reload(sys.modules['pipeline.plan_adjuster.adjuster'])
reload(sys.modules['pipeline.geometry_executor.executor']) 
# ... och så vidare för alla moduler ...


def process_sketch_to_shape(proto_data: bytes) -> 'Part.Shape':
    """
    Huvudfunktion som kör hela pipeline, från rådata till färdig 3D-modell.
    Detta är funktionen som ditt FreeCAD-makro kommer att anropa.
    """
    if not FREECAD_AVAILABLE:
        print("FEL: FreeCAD är inte tillgängligt. Avbryter.")
        return None # Returnera None om vi inte är i FreeCAD

    print("===================================")
    print("=== Startar Lineshape V2 Pipeline ===")
    print("===================================")
    
    try:
        # --- Steg 0: Ladda produktkatalogen ---
        # Katalogen laddas en gång och skickas sedan vidare till de moduler som behöver den.
        project_root = os.path.dirname(os.path.abspath(__file__))
        catalog_path = os.path.join(project_root, "components_catalog")
        
        print(f"Försöker ladda katalog från absolut sökväg: {catalog_path}")
        catalog = CatalogLoader(catalog_path)
        if not catalog.standards:
            print("FEL: Produktkatalogen kunde inte laddas eller är tom.")
            return None

        # --- Steg 1: Tolka skissen ---
        parser = SketchParser()
        parsed_sketch = parser.parse(proto_data)

        # --- Steg 2: Bygg topologin ---
        builder = TopologyBuilder(parsed_sketch, catalog)
        nodes, graph = builder.build()

        # --- Steg 3: Skapa byggplaner ---
        planner = BuildPlanner(nodes, graph, catalog)
        raw_plans = planner.create_plans()

        # --- Steg 4: Justera planer (ART) ---
        adjuster = PlanAdjuster(raw_plans, nodes, graph, catalog)
        adjusted_plans = adjuster.adjust_plans()

        # --- Steg 5: Exekvera och bygg 3D-modell ---
        # Detta är den modul vi nu ska börja implementera.
        executor = GeometryExecutor(
            adjusted_plans=adjusted_plans,
            nodes=nodes,
            catalog=catalog,
            freecad_part_module=Part,
            freecad_vector_class=Vector # Lägg till Vector-klassen här
        )
        final_shape = executor.build_model()
        
        print("===================================")
        print("=== Pipeline slutförd framgångsrikt ===")
        print("===================================")
        
        return final_shape

    except ImpossibleBuildError as e:
        print("\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print(f"FEL: Bygget är geometriskt omöjligt.")
        print(f"Anledning: {e}")
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n")
        return None
    except Exception as e:
        print(f"\nEtt oväntat fel inträffade i pipelinen: {e}")
        # Importera traceback för att kunna skriva ut mer detaljerade fel
        import traceback
        traceback.print_exc()
        return None