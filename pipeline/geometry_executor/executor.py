# pipeline/geometry_executor/executor.py

from typing import Any, List, Dict

# Inga direkta FreeCAD-importer här!
# Inga importer från andra pipeline-moduler behövs längre!

class GeometryExecutor:
    """
    Tar en geometriskt EXPLICIT byggplan (i rent Python-format) och
    omvandlar den till en 3D-modell i FreeCAD.
    Denna klass är en "dum" byggare som blint följer instruktionerna.
    Alla beroenden injiceras via __init__.
    """
    def __init__(self, explicit_plan: List[Dict[str, Any]], freecad_part_module: Any, freecad_vector_class: Any):
        """
        Konstruktorn tar emot en explicit plan och de nödvändiga FreeCAD-klasserna.
        """
        self.explicit_plan = explicit_plan
        self.Part = freecad_part_module
        self.Vector = freecad_vector_class

    def build_model(self) -> 'Part.Shape':
        """
        Huvudmetod som bygger en Part.Wire från den explicita planen.
        """
        if not self.Part or not self.Vector or not self.explicit_plan:
            print("VARNING: Executor - Nödvändiga moduler eller byggplan saknas.")
            return None

        print("  -> Executor: Bygger centrumlinje från explicit geometrisk plan...")
        edges = []

        for item in self.explicit_plan:
            item_type = item.get('type')
            
            try:
                if item_type == 'LINE':
                    start_vec = self.Vector(item['start'])
                    end_vec = self.Vector(item['end'])
                    line = self.Part.LineSegment(start_vec, end_vec)
                    edges.append(line.toShape())

                elif item_type == 'ARC':
                    start_vec = self.Vector(item['start'])
                    mid_vec = self.Vector(item['mid'])
                    end_vec = self.Vector(item['end'])
                    arc = self.Part.ArcOfCircle(start_vec, mid_vec, end_vec)
                    edges.append(arc.toShape())

            except Exception as e:
                print(f"    -> FEL: Kunde inte skapa geometriskt primitiv för item {item}. Fel: {e}")
                continue

        if not edges:
            print("VARNING: Inga kanter skapades för centrumlinjen.")
            return self.Part.Shape()
            
        return self.Part.Wire(edges)
