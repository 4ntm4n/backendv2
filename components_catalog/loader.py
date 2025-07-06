import json
import os
import math
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Union
import itertools

# --- Smarta Dataklasser med Inbyggd Beräkningslogik ---

@dataclass
class Bend90Data:
    """Dataklass för en 90-graders böj."""
    center_to_end: float
    bend_radius: float
    build_operation: str
    preferred_min_tangent: float

    @property
    def tangent(self) -> float:
        """Beräknar den initiala, ideala tangentlängden."""
        return max(0.0, self.center_to_end - self.bend_radius)
        
    @property
    def physical_min_tangent(self) -> float:
        """Den fysiska gränsen för kapning på en standardböj är alltid 0."""
        return 0.0

@dataclass
class Bend45Data:
    """Dataklass för en 45-graders böj."""
    b_dimension: float
    bend_radius: float
    build_operation: str
    preferred_min_tangent: float
    
    @property
    def center_to_end(self) -> float:
        """Beräknar det sanna Center-To-End-måttet."""
        # Using tan(67.5) is more direct for 45-degree bends with b-dimension
        return self.b_dimension * math.tan(math.radians(67.5))

    @property
    def tangent(self) -> float:
        """Beräknar den initiala, ideala tangentlängden."""
        # The tangent length is b_dimension
        return self.b_dimension

    @property
    def physical_min_tangent(self) -> float:
        """Den fysiska gränsen för kapning på en standardböj är alltid 0."""
        return 0.0

@dataclass
class TeeData:
    """Dataklass för ett T-rör."""
    equal_cte_run: float
    equal_cte_branch: float
    pipe_diameter: float
    build_operation: str
    preferred_min_tangent: float

    @property
    def physical_min_tangent(self) -> float:
        """Den fysiska gränsen för kapning på ett T-rör är halva rördiametern."""
        return self.pipe_diameter / 2.0

@dataclass
class ClampData:
    """Dataklass för en ändpunktskomponent som SMS Clamp."""
    tangent: float
    physical_min_tangent: float
    preferred_min_tangent: float
    sketch_file: str
    build_operation: str

@dataclass
class ReducerData:
    """Dataklass för en kona (reducer), genereras dynamiskt."""
    large_diameter: float
    small_diameter: float
    build_operation: str = "loft"

    @property
    def length(self) -> float:
        """Beräknar konans längd enligt standardformeln (A-B)*3."""
        if self.large_diameter > self.small_diameter:
            return (self.large_diameter - self.small_diameter) * 3.0
        return 0.0

    @property
    def physical_min_tangent(self) -> float:
        """En kona har inga tangenter och kan inte kapas."""
        return 0.0

# Typ-alias för alla möjliga komponent-dataklasser
ComponentData = Union[Bend90Data, Bend45Data, TeeData, ClampData, ReducerData]

@dataclass
class PipeSpecData:
    """Huvudklass som håller all data för en specifik rörstandard och dimension."""
    name: str
    diameter: float
    thickness: float
    bend_radius: float
    components: Dict[str, ComponentData] = field(default_factory=dict)

class CatalogLoader:
    """Läser in rådata från JSON och omvandlar den till smarta Python-objekt."""
    def __init__(self, catalog_path: str):
        self.standards: Dict[str, PipeSpecData] = {}
        if os.path.isdir(catalog_path):
            self._load_all(catalog_path)
        else:
            print(f"Error: Katalog-sökvägen '{catalog_path}' hittades inte eller är inte en mapp.")

    def _load_all(self, catalog_path: str):
        print("--- Laddar produktkatalog ---")
        for filename in os.listdir(catalog_path):
            if filename.endswith(".json"):
                filepath = os.path.join(catalog_path, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    try:
                        # Försök att ladda filen
                        data = json.load(f)
                    except json.JSONDecodeError:
                        # Om filen är tom eller ogiltig, hoppa över den och varna
                        print(f"VARNING: Filen '{filename}' är tom eller innehåller ogiltig JSON. Hoppar över.")
                        continue # Gå vidare till nästa fil

                    # Om filen laddades korrekt, fortsätt som vanligt
                    for spec_name_raw, spec_data in data.items():
                        spec_name_normalized = spec_name_raw.strip().replace('-', '_')
                        self.standards[spec_name_normalized] = self._parse_spec(spec_name_normalized, spec_data)
        
        self._generate_reducers()
        
        print(f"--- Katalog laddad med {len(self.standards)} specifikationer. ---")

    def _parse_spec(self, name: str, data: Dict) -> PipeSpecData:
        """Omvandlar en JSON-spec till ett smart PipeSpecData-objekt med nestlade komponent-objekt."""
        spec = PipeSpecData(
            name=name,
            diameter=data.get('diameter', 0.0),
            thickness=data.get('thickness', 0.0),
            bend_radius=data.get('bend_radius', 0.0)
        )
        
        default_preferred = data.get('default_preferred_min_tangent', 0.0)
        
        for comp_name, comp_data in data.get('components', {}).items():
            preferred_tangent = comp_data.get('preferred_min_tangent', default_preferred)
            build_op = comp_data.get('build_operation', 'unknown')

            if comp_name == "BEND_90":
                spec.components[comp_name] = Bend90Data(
                    center_to_end=comp_data['center_to_end'],
                    bend_radius=spec.bend_radius,
                    build_operation=build_op,
                    preferred_min_tangent=preferred_tangent
                )
            elif comp_name == "BEND_45":
                spec.components[comp_name] = Bend45Data(
                    b_dimension=comp_data['b_dimension'],
                    bend_radius=spec.bend_radius,
                    build_operation=build_op,
                    preferred_min_tangent=preferred_tangent
                )
            elif comp_name == "TEE":
                spec.components[comp_name] = TeeData(
                    equal_cte_run=comp_data['equal_cte_run'],
                    equal_cte_branch=comp_data['equal_cte_branch'],
                    pipe_diameter=spec.diameter,
                    build_operation=build_op,
                    preferred_min_tangent=preferred_tangent
                )
            elif comp_name == "SMS_CLAMP":
                spec.components[comp_name] = ClampData(
                    tangent=comp_data.get('tangent', 0.0),
                    physical_min_tangent=comp_data.get('min_tangent', 0.0),
                    preferred_min_tangent=preferred_tangent,
                    sketch_file=comp_data.get('sketch_file', ''),
                    build_operation=build_op
                )

        return spec

    def _generate_reducers(self):
        """Genererar dynamiskt alla möjliga kon-kombinationer baserat på laddade standarder."""
        print("--- Genererar konor (reducers)... ---")
        standard_names = list(self.standards.keys())
        
        for spec_name_a, spec_name_b in itertools.combinations(standard_names, 2):
            spec_a = self.standards[spec_name_a]
            spec_b = self.standards[spec_name_b]

            if spec_a.diameter == spec_b.diameter:
                continue

            if spec_a.diameter > spec_b.diameter:
                large_spec, small_spec = spec_a, spec_b
            else:
                large_spec, small_spec = spec_b, spec_a

            reducer_name = f"REDUCER_{int(large_spec.diameter)}_{int(small_spec.diameter)}"
            
            reducer_obj = ReducerData(
                large_diameter=large_spec.diameter,
                small_diameter=small_spec.diameter,
                build_operation="loft"
            )

            self.standards[spec_a.name].components[reducer_name] = reducer_obj
            self.standards[spec_b.name].components[reducer_name] = reducer_obj
            print(f"  -> Skapade '{reducer_name}' med längd {reducer_obj.length:.2f} mm.")

    def get_spec(self, spec_name: str) -> Optional[PipeSpecData]:
        """Hämtar en färdigbearbetad specifikation via dess namn (t.ex. 'SMS_25')."""
        return self.standards.get(spec_name)

if __name__ == '__main__':
    script_dir = os.path.dirname(__file__)
    catalog = CatalogLoader(script_dir)
    
    sms_51_spec = catalog.get_spec("SMS_51")
    if sms_51_spec:
        print("\n--- Testar genererade komponenter i SMS_51 ---")
        reducer = sms_51_spec.components.get("REDUCER_51_38")
        if reducer:
            print(f"Hittade: {reducer}")
            print(f"Beräknad längd: {reducer.length}")