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



# Arkitekturplan V2.1: En Tydlig Ansvarsfördelning

## 1. Grundläggande Filosofi

Efter analys av initiala implementationer har vi fastställt en ny, striktare arkitektonisk princip för att garantera ett robust och underhållbart system. Kärnan i denna princip är:

> **`GeometryExecutor` (Modul 5) ska vara en "dum" byggare.**

Detta innebär att all intelligens, all geometrisk beräkning och all justeringslogik måste vara slutförd *innan* Modul 5 anropas. Den slutgiltiga byggplanen som matas in till `Executor` får inte vara en semantisk lista med instruktioner, utan måste vara en **geometriskt explicit ritning** – en exakt, punkt-för-punkt-beskrivning av centrumlinjen.

Detta leder till följande, tydliga ansvarsfördelning mellan modulerna.

---

## 2. Modul 3: `BuildPlanner` (Logistikern)

Denna moduls ansvar förblir oförändrat, men det är viktigt att definiera dess strikta gränser.

* **Ansvar:** Att skapa en **logistisk "plocklista"**. Modulens enda jobb är att vandra genom den topologiska kartan (från Modul 2) och lista ut **i vilken ordning** komponenterna kommer.
* **Intelligens:** Expert på graf-traversering och hantering av förgreningar (T-rör).
* **Begränsning:** Helt omedveten om geometri, radier, byggmått eller exakta 3D-koordinater (utöver de som finns på noderna).
* **Output (Semantisk Byggplan):** En lista med `BuildPlanItem`-ordlistor som beskriver ordningsföljden.
    ```json
    [
      {"type": "COMPONENT", "component_name": "ENDPOINT", "node_id": "...", "spec_name": "SMS_25"},
      {"type": "STRAIGHT", "spec_name": "SMS_25"},
      {"type": "COMPONENT", "component_name": "BEND_90", "node_id": "...", "spec_name": "SMS_25"},
      {"type": "STRAIGHT", "spec_name": "SMS_25"},
      {"type": "COMPONENT", "component_name": "ENDPOINT", "node_id": "...", "spec_name": "SMS_25"}
    ]
    ```

---

## 3. Modul 4: `PlanAdjuster` (Geometri-Ingenjören)

Detta blir den mest centrala och intelligenta modulen i hela pipelinen. Den tar över ansvaret för all geometrisk beräkning.

* **Ansvar:** Att ta den logistiska plocklistan och omvandla den till en **exakt, geometrisk ritning**. Den innehåller den "mentala 3D-pennan".
* **Process:**
    1.  Tar emot den semantiska byggplanen från Modul 3.
    2.  Initierar en "3D-penna" vid startpunktens koordinater.
    3.  Itererar genom den semantiska planen, steg för steg.
    4.  För varje komponent (t.ex. en böj), beräknar den exakta 3D-koordinater för start-, mitt- och slutpunkter för den geometriska bågen, baserat på komponentens byggmått (`tangent_dist`).
    5.  För varje rakt rör, beräknar den den justerade längden och därmed dess start- och slutpunkt.
    6.  **Undantagshantering:** Om den under processen upptäcker ett geometriskt underskott (dvs. att delarna inte får plats), är det denna moduls ansvar att anropa sin interna `_handle_shortfall`-metod för att utföra den hierarkiska kapnings-algoritmen och justera de geometriska punkterna därefter.
* **Output (Geometriskt Explicit Byggplan):** En lista med exakta ritningsinstruktioner.
    ```json
    [
      {"type": "LINE", "start": [x1, y1, z1], "end": [x2, y2, z2]},
      {"type": "ARC",  "start": [x2, y2, z2], "mid": [x3, y3, z3], "end": [x4, y4, z4]},
      {"type": "LINE", "start": [x4, y4, z4], "end": [x5, y5, z5]}
    ]
    ```

---

## 4. Modul 5: `GeometryExecutor` (Den "Dumma" Byggaren)

Denna moduls ansvar förenklas radikalt för att uppfylla vår nya filosofi.

* **Ansvar:** Att **blint exekvera** den geometriskt explicita ritningen den får från Modul 4.
* **Intelligens:** Ingen. Den innehåller ingen egen "penna", ingen vektor-matematik och ingen logik för att beräkna positioner.
* **Process:** En simpel loop som mappar en `type` till ett FreeCAD-kommando.
* **Output:** Ett `Part.Wire`-objekt.

## 5. Fördelar med denna Arkitektur

* **Kristallklar Ansvarsfördelning:** Varje modul har ett väldefinierat och begränsat syfte.
* **Enkel Felsökning:** Om den slutgiltiga 3D-modellen är fel, kan felet **endast** ligga i den geometriska planen som `PlanAdjuster` producerade. Vi vet exakt var vi ska leta.
* **Testbarhet:** `PlanAdjuster` kan nu enhetstestas genom att verifiera att den producerar en korrekt lista av geometriska punkter, helt utan att behöva köra FreeCAD.
* **Robusthet:** Vi eliminerar risken för spagettikod som uppstår när flera moduler delar på ansvaret för geometrisk logik.



Jag håller med, vi tar det steg för steg, metod för metod.

Här är min föreslagna steg-för-steg-lista för att färdigställa PlanAdjuster enligt vår nya arkitektur. Målet är att få den att producera en perfekt, geometriskt explicit byggplan.

Steg-för-steg Plan för PlanAdjuster
Steg 1: Etablera "Den Mentala 3D-pennan"

Mål: Skapa den grundläggande loop-strukturen i _create_explicit_plan_from_semantic.

Implementation:

Metoden ska initiera en "penna" med en startposition (current_pos) och en startriktning (current_dir), baserat på den första noden i den semantiska planen.

Den ska sedan loopa igenom den semantiska planen, item för item.

Just nu kommer den inte att göra några beräkningar, men den kommer att ha rätt struktur för att kunna hantera STRAIGHT- och COMPONENT-items.

Resultat: Vi har en fungerande stomme, men den producerar fortfarande en tom plan.

Steg 2: Implementera Geometri för Raksträckor

Mål: Få pennan att kunna rita raka linjer med korrekt, justerad längd.

Implementation:

Inuti loopen från Steg 1, när vi stöter på ett STRAIGHT-item, ska vi implementera logiken från vårt senaste (misslyckade) test.

Vi tittar på komponenten före och efter det raka röret.

Vi beräknar deras "take-up" (byggmått) med en ny hjälpmetod _get_tangent_dist.

Vi beräknar det geometriska avståndet mellan komponenternas noder.

Vi beräknar den slutgiltiga, justerade längden: längd = avstånd - take_up1 - take_up2.

Vi skapar ett {'type': 'LINE', ...}-objekt med de korrekta start- och slutkoordinaterna och lägger till det i vår explicita plan. Pennans position uppdateras.

Resultat: Våra enklaste tester för raka rör och "happy path" bör nu passera. Vi kan nu korrekt rita rörsystem som endast består av raka rör.

Steg 3: Implementera Geometri för Böjar

Mål: Få pennan att kunna rita geometriskt korrekta böjar (tangenter och båge).

Implementation:

När loopen stöter på ett BEND-item, anropar vi en ny hjälpmetod, t.ex. _calculate_bend_primitives.

Denna metod kommer att innehålla den beprövade matematiken från din V1-kod.

Den tar emot pennans nuvarande position/riktning samt information om böjen (vinkel, radie).

Den beräknar och returnerar en lista med de geometriska primitiven för böjen: [LINE, ARC, LINE] (inkommande tangent, båge, utgående tangent).

Dessa primitiv läggs till i den explicita planen. Pennans position och riktning uppdateras till slutet av den sista tangenten.

Resultat: Vi kan nu korrekt rita rörsystem med både raka rör och böjar, förutsatt att allt får plats. Ditt test_adjuster_correctly_adjusts_internal_straights bör nu bli grönt.

Steg 4: Implementera Undantagshantering för Underskott (_handle_shortfall)

Mål: Hantera scenarion där den beräknade längden på ett rakt rör blir negativ.

Implementation:

I logiken för Steg 2, om adjusted_length blir negativ, anropar vi _handle_shortfall.

Denna metod kommer att innehålla den hierarkiska kapnings-logiken vi designat (försök med ett kap, komfort-kapning, nödvändighets-kapning).

VIKTIGT: Istället för att justera "längder", kommer denna metod att justera de geometriska koordinaterna för de primitiv som redan har skapats. Den "flyttar" på punkterna för att lösa underskottet.

Resultat: Hela PlanAdjuster är nu komplett. Den kan hantera alla scenarion och producerar alltid en geometriskt korrekt och byggbar ritning. Alla tester bör nu vara gröna.