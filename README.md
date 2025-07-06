# **Projektplan: lineshape-backend\_v2**

### **1\. Övergripande Arkitektur: "Pipeline"**

Hela logiken för att omvandla en skiss till en 3D-modell kommer att ligga i ett enda, väldefinierat Python-paket: pipeline. Detta paket innehåller alla våra moduler och utgör kärnan i applikationen.

### **2\. Slutgiltig Mappstruktur**

``` Bash
lineshape-backend\_v2/  
├── components\_catalog/  
│   ├── sms.json  
│   ├── iso.json  
│   └── loader.py  
├── contracts/  
│   └── ... (protobuf-filer)  
├── pipeline/  
│   ├── __init__.py  
│   ├──1_sketch_parser/  
│   │   ├── __init__.py  
│   │   └── parser.py  
│   ├── 2_topology_builder/  
│   │   ├── __init__.py  
│   │   ├── builder.py  
│   │   └── node_types_v2.py  
│   ├── 3_build_planner/  
│   │   ├── __init__.py  
│   │   └── planner.py  
│   ├── 4_plan_adjuster/  
│   │   ├── __init__.py  
│   │   └── adjuster.py  
│   ├── 5_geometry_executor/  
│   │   ├── __init__.py  
│   │   └── executor.py  
│   └── shared/  
│       ├── __init__.py  
│       └── types.py  
└── tests/  
    └── ... (enhetstester för varje modul)
```



### **3\. Modulöversikt och Ansvarsområden**

* **components\_catalog/**: Innehåller rådata för alla komponenter i JSON-filer och en loader.py för att läsa in dem.  
* **pipeline/sketch\_parser/**: **Modul 1\.** Översätter rå Protobuf-data till en ren Python-dictionary.  
* **pipeline/topology\_builder/**: **Modul 2\.** Bygger den intelligenta networkx-kartan från den rena skissdatan. Innehåller logik för 2D-till-3D-översättning och nodklassificering.  
* **pipeline/build\_planner/**: **Modul 3\.** Läser kartan och skapar en eller flera linjära byggplaner.  
* **pipeline/plan\_adjuster/**: **Modul 4\.** Tar byggplanerna och justerar dem för att matcha exakta mått (ART).  
* **pipeline/geometry\_executor/**: **Modul 5\.** Den enda modulen som pratar med FreeCAD. Läser den slutgiltiga planen och bygger 3D-modellen.  
* **pipeline/shared/**: Innehåller gemensamma datatyper, som BuildPlanItem, som används mellan modulerna.