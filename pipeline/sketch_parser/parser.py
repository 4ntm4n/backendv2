# pipeline/1_sketch_parser/parser.py

from typing import Dict, Any, List, Optional

# Importera den genererade protobuf-klassen.
# Denna sökväg förutsätter att skript som använder denna klass körs
# från projektets rotmapp (lineshape-backend_v2/).
from contracts.generated.python import sketch_pb2

class SketchParser:
    """
    Ansvarar för att tolka rå Protobuf-data från frontend och omvandla
    den till en ren, intern Python-datastruktur.
    """
    def __init__(self):
        """Initialiserar parsern."""
        pass

    def parse(self, protobuf_data: bytes) -> Dict[str, Any]:
        """
        Huvudmetod som utför tolkningen.

        Args:
            protobuf_data: De råa byten från frontend-requesten.

        Returns:
            En dictionary som representerar den tolkade skissen.
            Returnerar en tom struktur vid fel.
        """
        print("--- Modul 1 (Sketch Parser): Startar tolkning av Protobuf-data ---")
        
        # 1. Deserialisera Protobuf-meddelandet
        try:
            sketch_data_proto = sketch_pb2.SketchData()
            sketch_data_proto.ParseFromString(protobuf_data)
        except Exception as e:
            print(f"    -> FEL: Kunde inte tolka Protobuf-data. Fel: {e}")
            # Returnera en tom struktur för att undvika krascher längre fram i pipelinen.
            return {"segments": [], "origin": None}

        # 2. Omvandla till vår rena, interna Python-struktur
        parsed_sketch = {
            "segments": [],
            "origin": None
        }

        for segment_proto in sketch_data_proto.segments:
            # Säkerställ att ID och specifikation finns
            if not segment_proto.id or not segment_proto.pipe_spec:
                print(f"    -> VARNING: Segment saknar 'id' eller 'pipe_spec'. Hoppar över.")
                continue

            parsed_segment = {
                "id": segment_proto.id,
                "start_point": (segment_proto.startPoint.x, segment_proto.startPoint.y),
                "end_point": (segment_proto.endPoint.x, segment_proto.endPoint.y),
                # Normalisera spec-namnet för konsekvent användning
                "pipe_spec": segment_proto.pipe_spec.strip().replace('-', '_'),
                # Hantera det optionella längd-fältet
                "length_dimension": segment_proto.length_dimension if segment_proto.HasField('length_dimension') else None,
                "is_construction": segment_proto.isConstruction
            }
            parsed_sketch["segments"].append(parsed_segment)
        
        if sketch_data_proto.HasField('userDefinedOrigin'):
            parsed_sketch["origin"] = (
                sketch_data_proto.userDefinedOrigin.x,
                sketch_data_proto.userDefinedOrigin.y
            )
            
        print(f"--- Sketch Parser: Tolkning klar. {len(parsed_sketch['segments'])} giltiga segment hittade. ---")
        
        return parsed_sketch