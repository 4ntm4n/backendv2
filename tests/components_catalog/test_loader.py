import pytest
import json

# Importera klasserna vi vill testa
from components_catalog.loader import (
    CatalogLoader,
    TeeData,
    ClampData,
    Bend90Data,
    ReducerData
)

@pytest.fixture
def mock_catalog_path(tmp_path):
    """
    Skapar en tillfällig katalog med en mock-JSON-fil för testerna.
    Detta gör testet robust och oberoende av den verkliga filstrukturen.
    """
    catalog_dir = tmp_path / "test_catalog"
    catalog_dir.mkdir()
    
    # Använd innehållet från vår uppdaterade sms.json
    mock_data = {
      "SMS_25": {
        "diameter": 25.0, "thickness": 1.2, "bend_radius": 38.0,
        "default_preferred_min_tangent": 12.5,
        "components": {
          "BEND_90": {"center_to_end": 51.0, "build_operation": "sweep_arc"},
          "TEE": {"equal_cte_run": 51.0, "equal_cte_branch": 51.0, "build_operation": "build_tee_solid"},
          "SMS_CLAMP": {"tangent": 20.0, "min_tangent": 8.0, "preferred_min_tangent": 15.0, "build_operation": "revolve"}
        }
      },
      "SMS_38": {
        "diameter": 38.0, "thickness": 1.2, "bend_radius": 57.0,
        "default_preferred_min_tangent": 12.5,
        "components": {}
      },
      "SMS_51": {
        "diameter": 51.0, "thickness": 1.2, "bend_radius": 76.0,
        "default_preferred_min_tangent": 12.5,
        "components": {}
      }
    }

    json_file = catalog_dir / "sms.json"
    json_file.write_text(json.dumps(mock_data))
    
    return str(catalog_dir)

def test_loader_instantiation_and_reducer_generation(mock_catalog_path):
    """
    GIVEN: En mock-katalog med tre SMS-standarder.
    WHEN:  CatalogLoader initieras.
    THEN:  Alla standarder ska laddas OCH alla kona-kombinationer ska genereras.
    """
    # ACT
    catalog = CatalogLoader(mock_catalog_path)
    
    # ASSERT - Grundläggande laddning
    assert "SMS_25" in catalog.standards
    assert "SMS_38" in catalog.standards
    assert "SMS_51" in catalog.standards
    
    # ASSERT - Att konor har genererats korrekt
    sms_51_spec = catalog.get_spec("SMS_51")
    sms_38_spec = catalog.get_spec("SMS_38")
    sms_25_spec = catalog.get_spec("SMS_25")
    
    # Kontrollera att konorna finns i ALLA relevanta standarder
    assert "REDUCER_51_38" in sms_51_spec.components
    assert "REDUCER_51_38" in sms_38_spec.components
    
    assert "REDUCER_51_25" in sms_51_spec.components
    assert "REDUCER_51_25" in sms_25_spec.components

    assert "REDUCER_38_25" in sms_38_spec.components
    assert "REDUCER_38_25" in sms_25_spec.components

def test_reducer_data_properties(mock_catalog_path):
    """
    GIVEN: En initierad CatalogLoader.
    WHEN:  Vi hämtar ett genererat ReducerData-objekt.
    THEN:  Dess längd ska vara korrekt beräknad enligt formeln (A-B)*3.
    """
    # ARRANGE
    catalog = CatalogLoader(mock_catalog_path)
    
    # ACT
    reducer_51_38 = catalog.get_spec("SMS_51").components.get("REDUCER_51_38")
    
    # ASSERT
    assert isinstance(reducer_51_38, ReducerData)
    expected_length = (51.0 - 38.0) * 3.0
    assert reducer_51_38.length == pytest.approx(expected_length) # 13 * 3 = 39

def test_component_tangent_logic(mock_catalog_path):
    """
    GIVEN: En initierad CatalogLoader.
    WHEN:  Vi hämtar olika komponenter från SMS_25-specifikationen.
    THEN:  Deras preferred och physical min-tangenter ska vara korrekta.
    """
    # ARRANGE
    catalog = CatalogLoader(mock_catalog_path)
    spec = catalog.get_spec("SMS_25")

    # --- Test 1: BEND_90 ärver standardvärdet ---
    bend = spec.components.get("BEND_90")
    assert isinstance(bend, Bend90Data)
    assert bend.preferred_min_tangent == 12.5 # Ärvd från default
    assert bend.physical_min_tangent == 0.0   # Beräknad i kod

    # --- Test 2: TEE beräknar physical, ärver preferred ---
    tee = spec.components.get("TEE")
    assert isinstance(tee, TeeData)
    assert tee.preferred_min_tangent == 12.5 # Ärvd från default
    assert tee.physical_min_tangent == 25.0 / 2.0 # Beräknad från diameter

    # --- Test 3: SMS_CLAMP åsidosätter preferred, har fast physical ---
    clamp = spec.components.get("SMS_CLAMP")
    assert isinstance(clamp, ClampData)
    assert clamp.preferred_min_tangent == 15.0 # Åsidosatt i JSON
    assert clamp.physical_min_tangent == 8.0   # Fast värde från JSON