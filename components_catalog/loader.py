# components_catalog/loader.py

import json
import os
import math
from dataclasses import dataclass, field
from typing import Dict, Any, Optional

# --- Smarta Dataklasser med Beräknade Egenskaper ---

@dataclass
class BaseComponentData:
    """Grundklass för all komponentdata."""
    build_operation: str

@dataclass
class BendData(BaseComponentData):
    """Håller rådata för en böj och beräknar dess tangent."""
    center_to_end: Optional[float] = None
    b_dimension: Optional[float] = None
    bend_radius: float = 0.0 # Får detta värde från sin förälder (PipeSpecData)

    @property
    def tangent(self) -> float:
        """Beräknar tangentlängden baserat på böjtyp, med logik från V1."""
        # 90-graders böj
        if self.center_to_end is not None:
            return max(0.0, self.center_to_end - self.bend_radius)
        # 45-graders böj
        elif self.b_dimension is not None:
            center_to_end_45 = self.b_dimension * math.sqrt(2)
            tangent_dist_45_calc = self.bend_radius / (math.tan(math.radians(45) / 2.0))
            return max(0.0, center_to_end_45 - tangent_dist_45_calc)
        return 0.0

@dataclass
class TeeData(BaseComponentData):
    """Håller data för ett T-rör."""
    equal_cte_run: float
    equal_cte_branch: float
    # TODO: Lägg till logik för reducerade T-rör här senare

@dataclass
class EndpointData(BaseComponentData):
    """Håller data för en ändpunktskoppling."""
    tangent: float
    min_tangent: float
    sketch_file: Optional[str] = None

# ... Fler dataklasser för Reducer, WeldCap etc. kan läggas till här ...

@dataclass
class PipeSpecData:
    """Huvudklass som håller all data för en specifik rördimension."""
    name: str
    diameter: float
    thickness: float
    bend_radius: float
    components: Dict[str, Any] = field(default_factory=dict)

class CatalogLoader:
    """Läser in JSON-filer och omvandlar dem till smarta, lätthanterliga Python-objekt."""
    def __init__(self, catalog_path: str):
        self.standards: Dict[str, PipeSpecData] = {}
        self._load_all(catalog_path)

    def _load_all(self, catalog_path: str):
        print("--- Modul 0 (CatalogLoader): Laddar produktkatalog ---")
        for filename in os.listdir(catalog_path):
            if filename.endswith(".json"):
                filepath = os.path.join(catalog_path, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for spec_name, spec_data in data.items():
                        # Använd det tvättade namnet som nyckel
                        cleaned_name = spec_name.strip().replace('-', '_')
                        self.standards[cleaned_name] = self._parse_spec(cleaned_name, spec_data)
        print(f"--- Katalog laddad. {len(self.standards)} specifikationer tillgängliga. ---")

    def _parse_spec(self, name: str, data: Dict) -> PipeSpecData:
        """Omvandlar en JSON-spec till ett smart PipeSpecData-objekt."""
        spec = PipeSpecData(
            name=name,
            diameter=data['diameter'],
            thickness=data['thickness'],
            bend_radius=data['bend_radius']
        )
        
        for comp_name, comp_data in data['components'].items():
            build_op = comp_data.get('build_operation', 'unknown')
            
            if "BEND" in comp_name:
                spec.components[comp_name] = BendData(
                    build_operation=build_op,
                    center_to_end=comp_data.get('center_to_end'),
                    b_dimension=comp_data.get('b_dimension'),
                    bend_radius=spec.bend_radius
                )
            elif "TEE" in comp_name:
                spec.components[comp_name] = TeeData(build_operation=build_op, **comp_data)
            elif "SMS_CLAMP" in comp_name:
                 spec.components[comp_name] = EndpointData(build_operation=build_op, **comp_data)
            # ... elif för andra komponenter ...
            
        return spec

    def get_spec(self, spec_name: str) -> Optional[PipeSpecData]:
        return self.standards.get(spec_name)
