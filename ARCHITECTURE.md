# **Designplan: backendv2**

Detta dokument beskriver den övergripande arkitekturen och den detaljerade designen för varje modul i backendv2-projektet.

## **Modul 1: Tolkaren (**SketchParser**)**

### **1\. Syfte och Ansvar**

* **Syfte:** Att agera som en robust och pålitlig "översättare" mellan den råa, tekniska Protobuf-datan från frontend och resten av backendens rena Python-miljö.  
* **Enskilt Ansvar:** Modulens enda ansvar är att tolka det inkommande protobuf\-meddelandet och omvandla det till en enkel, intern och lätthanterlig Python-datastruktur. Den ska identifiera bygghjälpslinjer (isConstruction) men **inte** tolka deras innebörd. Den är en ren dataomvandlare, inget annat.

### **2\. Dataflöde**

* **Indata:** Ett rått bytes\-objekt som innehåller en serialiserad SketchData\-protokollbuffert (definierad i contracts/proto/sketch.proto).  
* **Utdata:** En enkel Python-ordlista (dict) som representerar skissen på ett rent sätt. Detta format är lätt att enhetstesta och konsumera för nästa modul i kedjan.

### **3\. Design av Utdata**

Strukturen säkerställer att all nödvändig information från skissen, inklusive isConstruction\-flaggan, finns tillgänglig på ett konsekvent och lättillgängligt sätt.

\# Exempel på den rena data som SketchParser producerar  
parsed\_sketch \= {  
    "segments": \[  
        {  
            "id": "l1",  
            "start\_point": (242.4871, 420.0), \# Notera: en tuple, inte en dict  
            "end\_point": (242.4871, 260.0),  
            "pipeSpec": "SMS-38",  
            "length\_dimension": 500.0,  
            "isConstruction": False  
        },  
        {  
            "id": "c1", \# Konstruktionslinjer kan ha egna ID:n  
            "start\_point": (242.4871, 260.0),  
            "end\_point": (415.6922, 160.0),  
            "pipeSpec": "SMS-38",  
            "length\_dimension": 200.0,  
            "isConstruction": True \# Denna linje är en bygghjälpslinje  
        }  
        \# ... fler segment  
    \],  
    "origin": (100.0, 100.0) \# Optionell, om definierad av användaren  
}

### **4\. Kodskelett (**parser.py**)**

Implementationen är rakt på sak och fokuserar enbart på att översätta fält från protobuf-objektet till en Python-dictionary. Den hanterar även fall där optionella fält (som length\_dimension) saknas.

\# backendv2/pipeline/1\_sketch\_parser/parser.py

from typing import Dict, Any, List, Optional  
\# Importerar den genererade protobuf-klassen  
from contracts.generated.python import sketch\_pb2

class SketchParser:  
    """  
    Ansvarar för att tolka rå Protobuf-data och omvandla den till en  
    ren, intern Python-datastruktur.  
    """  
    def parse(self, protobuf\_data: bytes) \-\> Dict\[str, Any\]:  
        """  
        Huvudmetod som utför tolkningen.  
        """  
        print("--- Modul 1 (SketchParser): Startar tolkning av Protobuf-data \---")

        sketch\_data\_proto \= sketch\_pb2.SketchData()  
        sketch\_data\_proto.ParseFromString(protobuf\_data)

        parsed\_sketch \= {"segments": \[\]}

        for segment\_proto in sketch\_data\_proto.segments:  
            parsed\_segment \= {  
                "id": segment\_proto.id,  
                "start\_point": (segment\_proto.startPoint.x, segment\_proto.startPoint.y),  
                "end\_point": (segment\_proto.endPoint.x, segment\_proto.endPoint.y),  
                "pipeSpec": segment\_proto.pipe\_spec,  
                "length\_dimension": segment\_proto.length\_dimension if segment\_proto.HasField('length\_dimension') else None,  
                "isConstruction": segment\_proto.isConstruction  
            }  
            parsed\_sketch\["segments"\].append(parsed\_segment)

        if sketch\_data\_proto.HasField('userDefinedOrigin'):  
            parsed\_sketch\["origin"\] \= (  
                sketch\_data\_proto.userDefinedOrigin.x,  
                sketch\_data\_proto.userDefinedOrigin.y  
            )

        print(f"--- SketchParser: Tolkning klar. {len(parsed\_sketch\['segments'\])} segment hittade. \---")  
        return parsed\_sketch

### **5\. Sammanfattning och Gränssnitt mot Nästa Modul**

Denna design ger oss en extremt robust och pålitlig start på vår pipeline. Genom att den bara har ett enda, tydligt ansvar blir den enkel att förstå, underhålla och testa. Nästa modul, TopologyBuilder, kan lita på att den alltid får en konsekvent formaterad lista med segment, redo för den mer komplexa uppgiften att bygga en topologisk karta.

## **Modul 2: Kartografen (**TopologyBuilder**)**

### **1\. Syfte och Ansvar**

* **Syfte:** Att agera som systemets "kartograf" och "geometri-ingenjör". Denna modul tar den rena 2D-skissdatan och bygger en komplett, tredimensionell och intelligent topologisk representation av hela rörsystemet.  
* **Enskilt Ansvar:**  
  1. **Topologi-förståelse:** Att först bygga en 2D-graf av skissen för att förstå alla kopplingar, oberoende av ritningsordning.  
  2. **3D-Översättning:** Att översätta den sammanhängande 2D-kartan till en korrekt 3D-graf, inklusive all hjälpgometri.  
  3. **Förenkling & Rensning:** Att först hantera "Construction Chains" för att skapa speciallinjer, och därefter **ta bort all hjälpgometri** för att producera en ren graf.  
  4. **Berikning:** Att analysera den slutgiltiga, rena grafen och berika dess noder med all nödvändig metadata (nodtyp, vinklar, specifikationer etc.).

### **2\. Dataflöde**

* **Indata:** parsed\_sketch\-ordlistan från SketchParser (Modul 1).  
* **Utdata:** En tuple som innehåller (nodes\_list, final\_topology\_graph).  
  * nodes\_list: En lista med färdiganalyserade NodeInfo\-objekt (BendNodeInfo, TeeNodeInfo, etc.).  
  * final\_topology\_graph: En networkx\-graf som representerar den slutgiltiga, rena 3D-topologin. Detta är systemets "Single Source of Truth" för resten av pipelinen.

### **3\. Logiskt Flöde**

Modulen arbetar i en robust, sekventiell process för att garantera ett korrekt resultat.

1. **Pass 1: Bygg 2D-Karta:** Modulen ignorerar först all 3D-information. Den bygger en komplett networkx\-graf baserad **enbart** på 2D-koordinaterna från indatan. Detta säkerställer att alla anslutningar identifieras korrekt och löser problemet med frånkopplade "öar".  
2. **Pass 2: Översätt till 3D:** Med den kompletta 2D-kartan som guide, "vandrar" modulen genom skissen från en stabil startpunkt och bygger upp en komplett 3D-graf som inkluderar **alla** linjer (både vanliga och konstruktionslinjer).  
3. **Pass 3: Hantera Specialgeometri (Construction Chains):** Modulen söker efter mönster av isConstruction: true\-linjer som utgör en "byggnadsställning" och ersätter dem med en enda, korrekt "speciallinje". Detta lämnar kvar en graf där vissa hjälplinjer har tjänat sitt syfte.  
   * **Implementation:** Logiken för att hitta dessa kedjor ska baseras på den beprövade sök-funktionen från spagettikodspiloten.  
   * **Referenskod:**  
     \# Koncept från tidigare fungerande logik  
     def find\_construction\_chain(start\_node, end\_node, graph):  
         \# Sök efter en kedja med 2 eller 3 konstruktionslinjer...  
         \# Om en kedja hittas, returnera den.  
         pass  
     \`\`\`python  
     \# Konkret exempel från en fungerande prototyp av construction chain tekniken.  
     def find\_json\_construction\_chain( start\_node\_2d\_tuple: Tuple\[float, float\], end\_node\_2d\_tuple: Tuple\[float, float\], graph: Dict\[Tuple\[float, float\], List\[Dict\[str, Any\]\]\], max\_len: int \= 3\) \-\> Optional\[List\[Dict\[str, Any\]\]\]:  
         if start\_node\_2d\_tuple not in graph: return None  
         for conn1 in graph.get(start\_node\_2d\_tuple, \[\]):  
             if conn1.get("is\_construction", False):  
                 mid\_node1\_2d\_tuple \= conn1.get("neighbor\_2d\_tuple")  
                 if mid\_node1\_2d\_tuple is None or mid\_node1\_2d\_tuple not in graph: continue  
                 for conn2 in graph.get(mid\_node1\_2d\_tuple, \[\]):  
                     neighbor2\_2d\_tuple \= conn2.get("neighbor\_2d\_tuple")  
                     if neighbor2\_2d\_tuple is None: continue  
                     if conn2.get("is\_construction", False) and \\  
                        conn2.get("index") \!= conn1.get("index") and \\  
                        json\_points\_equal(neighbor2\_2d\_tuple, end\_node\_2d\_tuple):  
                         return \[conn1, conn2\]  
         if max\_len \>= 3:  
             for conn1 in graph.get(start\_node\_2d\_tuple, \[\]):  
                 if conn1.get("is\_construction", False):  
                     mid\_node1\_2d\_tuple \= conn1.get("neighbor\_2d\_tuple")  
                     if mid\_node1\_2d\_tuple is None or mid\_node1\_2d\_tuple not in graph: continue  
                     for conn2 in graph.get(mid\_node1\_2d\_tuple, \[\]):  
                         if conn2.get("is\_construction", False) and conn2.get("index") \!= conn1.get("index"):  
                             mid\_node2\_2d\_tuple \= conn2.get("neighbor\_2d\_tuple")  
                             if mid\_node2\_2d\_tuple is None or mid\_node2\_2d\_tuple not in graph: continue  
                             for conn3 in graph.get(mid\_node2\_2d\_tuple, \[\]):  
                                 neighbor3\_2d\_tuple \= conn3.get("neighbor\_2d\_tuple")  
                                 if neighbor3\_2d\_tuple is None: continue  
                                 if conn3.get("is\_construction", False) and \\  
                                    conn3.get("index") \!= conn2.get("index") and \\  
                                    json\_points\_equal(neighbor3\_2d\_tuple, end\_node\_2d\_tuple):  
                                     return \[conn1, conn2, conn3\]  
         return None

4. **Pass 4: Rensning av Hjälpgeometri:** Som ett sista städsteg går modulen igenom grafen och **tar bort alla återstående kanter** som är flaggade med is\_construction: true. Detta inkluderar både de använda "chain"-linjerna och eventuella "offset"-linjer.  
5. **Pass 5: Berika Noder:** Modulen analyserar den slutgiltiga, rena 3D-grafen. Den klassificerar varje nod (hörn) baserat på antalet anslutningar (Endpoint, Bend, Tee), beräknar vinklar, och flaggar noder som kräver en övergång (requires\_reducer).

### **4\. Kodskelett (**builder.py**)**

Kodstrukturen reflekterar denna nya, utökade flerstegsprocess.

\# backendv2/pipeline/2\_topology\_builder/builder.py

class TopologyBuilder:  
    \# ... (\_\_init\_\_) ...

    def build(self) \-\> Tuple\[List\[NodeInfo\], nx.Graph\]:  
        """Huvudmetod som orkestrerar byggprocessen."""  
        print("--- Modul 2 (TopologyBuilder): Startar \---")

        two\_d\_graph \= self.\_build\_2d\_graph\_from\_sketch()  
        print(f"  \-\> Pass 1: Komplett 2D-graf skapad.")

        self.\_translate\_graph\_to\_3d(two\_d\_graph)  
        print(f"  \-\> Pass 2: Graf översatt till 3D.")

        self.\_simplify\_graph\_patterns()  
        print(f"  \-\> Pass 3: Specialgeometri hanterad.")

        self.\_remove\_construction\_geometry() \# NYTT STEG  
        print(f"  \-\> Pass 4: Hjälpgeometri borttagen.")

        self.\_enrich\_nodes()  
        print(f"  \-\> Pass 5: Noder klassificerade och berikade.")  
          
        print("--- TopologyBuilder: Klar \---")  
        return self.nodes, self.topology

    \# ... (\_build\_2d\_graph\_from\_sketch, \_translate\_graph\_to\_3d, etc.) ...

    def \_remove\_construction\_geometry(self):  
        """NY HJÄLPMETOD: Rensar grafen från all hjälpgometri."""  
        pass

### **5\. Sammanfattning och Gränssnitt mot Nästa Modul**

Genom att separera topologi-förståelse, 3D-översättning, förenkling och rensning, skapar denna modul en extremt pålitlig grund för resten av systemet. Planner\-modulen (nästa steg) kan fullständigt lita på att den graf den tar emot är en komplett, korrekt och intelligent representation av **endast** den faktiska rörgeometrin.

## **Modul 3: Reseplaneraren (**Planner**)**

### **1\. Syfte och Ansvar**

* **Syfte:** Att agera som systemets "logistiker". Den tar den komplexa, icke-linjära topologiska kartan från TopologyBuilder och översätter den till en eller flera enkla, linjära och sekventiella "resplaner".  
* **Enskilt Ansvar:**  
  1. **Traversering:** Att på ett intelligent sätt "vandra" genom networkx\-grafen från startpunkter till slutpunkter.  
  2. **Hantering av förgreningar:** Att kunna identifiera förgreningspunkter (T-rör) och korrekt skapa separata resplaner för varje gren i rörsystemet.  
  3. **Skapa Sekvens:** Att översätta den topologiska vägen till en enkel lista av instruktioner (en sekvens av nod- och kant-ID:n). Modulen berikar **inte** datan ytterligare; den bestämmer endast **ordningen**.

### **2\. Dataflöde**

* **Indata:** En tuple som innehåller (nodes\_list, final\_topology\_graph) från TopologyBuilder (Modul 2).  
* **Utdata:** En lista av resplaner (List\[List\[Dict\[str, str\]\]\] ). Varje inre lista är en komplett, sekventiell resplan för en enskild, kontinuerlig rörgren.

### **3\. Design av Utdata**

Utdata är en enkel lista av instruktioner, designad för att vara lätt att följa för nästa modul (CenterlineBuilder).

\# Exempel på den rena data som Planner producerar  
list\_of\_plans \= \[  
    \# Plan för huvudgrenen  
    \[  
        {'type': 'NODE', 'id': 'node\_id\_1'},  
        {'type': 'EDGE', 'id': ('node\_id\_1', 'node\_id\_2')},  
        {'type': 'NODE', 'id': 'node\_id\_2'}, \# Detta är en T-korsning  
        {'type': 'EDGE', 'id': ('node\_id\_2', 'node\_id\_3')},  
        {'type': 'NODE', 'id': 'node\_id\_3'},  
    \],  
    \# Plan för avsticket från T-korsningen  
    \[  
        {'type': 'NODE', 'id': 'node\_id\_2'}, \# Startar från samma T-korsning  
        {'type': 'EDGE', 'id': ('node\_id\_2', 'node\_id\_4')},  
        {'type': 'NODE', 'id': 'node\_id\_4'},  
    \]  
\]

### **4\. Logiskt Flöde**

Modulen använder en systematisk algoritm för att säkerställa att alla delar av rörsystemet planeras.

1. **Hitta Startpunkter:** Planeraren börjar med att identifiera alla noder som är ändpunkter (EndpointNodeInfo) i grafen. Varje sådan nod är en potentiell startpunkt för en resplan.  
2. **Bearbeta Gren för Gren:** Den loopar igenom varje startpunkt. För att undvika att planera samma gren två gånger (från båda ändar), håller den reda på vilka kanter som redan har inkluderats i en plan.  
3. **Vandra och Bygg Planen:** Från en startpunkt påbörjas en "vandring" genom grafen.  
   * Den följer vägen från nod till nod och lägger till {'type': 'NODE', ...} och {'type': 'EDGE', ...} i den nuvarande resplanen.  
   * **Hantering av T-rör:** När vandringen når en TeeNodeInfo, använder den den berikade informationen från TopologyBuilder för att identifiera huvudflödet ("the run") och avsticket ("the branch"). Den fortsätter vandringen längs huvudflödet. Samtidigt noterar den att en ny, separat plan måste skapas för avsticket senare.  
4. **Slutförande:** När en vandring når en slutpunkt är den nuvarande resplanen klar. Processen fortsätter tills alla grenar i systemet har fått en egen, komplett resplan.

### **5\. Kodskelett (**planner.py**)**

\# backendv2/pipeline/3\_build\_planner/planner.py  
from typing import Dict, Any, List, Tuple  
import networkx as nx  
from ..topology\_builder.node\_types\_v2 import NodeInfo, EndpointNodeInfo, TeeNodeInfo

class Planner:  
    """  
    Översätter en berikad topologi-graf till en lista av sekventiella resplaner.  
    """  
    def \_\_init\_\_(self, nodes: List\[NodeInfo\], topology: nx.Graph):  
        self.nodes \= nodes  
        self.nodes\_by\_id \= {node.id: node for node in nodes}  
        self.topology \= topology  
        self.visited\_edges \= set() \# För att undvika dubbelplanering

    def create\_travel\_plans(self) \-\> List\[List\[Dict\[str, Any\]\]\]:  
        """  
        Huvudmetod som hittar alla startpunkter och genererar en resplan för varje gren.  
        """  
        print("--- Modul 3 (Planner): Startar \---")  
        all\_plans: List\[List\[Dict\[str, Any\]\]\] \= \[\]  
          
        start\_nodes \= \[node for node in self.nodes if isinstance(node, EndpointNodeInfo)\]  
          
        for start\_node in start\_nodes:  
            \# Kontrollera om denna gren redan har planerats  
            start\_edge\_nodes \= list(self.topology.neighbors(start\_node.id))  
            if not start\_edge\_nodes: continue  
              
            start\_edge \= tuple(sorted((start\_node.id, start\_edge\_nodes\[0\])))  
            if start\_edge in self.visited\_edges:  
                continue

            \# Bygg planen för denna nya, oplanerade gren  
            plan \= self.\_traverse\_and\_build\_plan(start\_node)  
            all\_plans.append(plan)  
              
        print(f"--- Planner: Klar. {len(all\_plans)} resplan(er) skapade. \---")  
        return all\_plans

    def \_traverse\_and\_build\_plan(self, start\_node: NodeInfo) \-\> List\[Dict\[str, Any\]\]:  
        """  
        PLATSHÅLLARE: Implementerar "vandringen" för att bygga en enskild plan.  
        """  
        print(f"  \-\> Bygger resplan som startar från nod {start\_node.id\[:8\]}...")  
        \# TODO: Implementera den faktiska traverseringslogiken här.  
        \# Denna logik ska följa grafen, hantera T-korsningar intelligent,  
        \# och bygga upp listan av instruktioner.  
        return \[\]

### **6\. Sammanfattning och Gränssnitt mot Nästa Modul**

Planner\-modulen agerar som en ren logistiker. Den tar en komplex karta och skapar enkla, linjära "körscheman". Nästa modul, ComponentFactory, kommer inte att anropas av denna modul, utan av CenterlineBuilder som kommer att använda dessa körscheman som sin guide.

## **Modul 4: Komponent-specialisten (**ComponentFactory**)**

### **1\. Syfte och Ansvar**

* **Syfte:** Att agera som ett centraliserat och isolerat "bibliotek" för all domänspecifik komponentlogik. Detta är vår "bransch-bibel" i kodform.  
* **Enskilt Ansvar:** Att, för en given komponenttyp (t.ex. en 90-gradersböj) och specifikation, beräkna och returnera den exakta **lokala centrumlinje-geometrin** för just den komponenten. Detta inkluderar att **tagga** varje geometrisk primitiv med den korrekta build\_operation (t.ex. "sweep") som behövs för 3D-rendering.

### **2\. Dataflöde**

* **Indata (per metodanrop):** En NodeInfo\-subklass (som BendNodeInfo) som innehåller information om vinkel och rörspecifikation.  
* **Utdata (per metodanrop):** En standardiserad lista av geometriska primitiv (LINE, ARC) som representerar komponentens lokala centrumlinje, redo att användas av CenterlineBuilder. Varje primitiv är "taggad" med sin build\_operation.

### **3\. Logiskt Flöde och Beräkningsprinciper**

ComponentFactory är inte en del av den sekventiella pipelinen, utan en "on-demand"-tjänst. Dess logik bygger på att separera rådata från beräkningar och använder en objektorienterad struktur för maximal återanvändbarhet och utbyggbarhet.

1. **Rådata från Katalog:** Katalogen (JSON-filer) innehåller endast rådata från tillverkaren, såsom center\_to\_end (CTE) för en 90-gradersböj, eller b\_dimension för en 45-gradersböj.  
2. **Beräkning i Fabriken (via klasser):** Fabriken använder en hierarki av klasser för att hantera olika komponenttyper.  
   * **Basklass (**BendComponent**):** Innehåller all gemensam logik för alla böjar. Den vet hur man beräknar en tangent från ett CTE-mått och en radie (tangent \= CTE \- radius). Den innehåller också den grundläggande logiken för att placera en böjs centrum.  
   * **Subklasser (**Bend90**,** Bend45**,** CustomAngleBend**):** Dessa klasser ärver från BendComponent.  
     * Bend45 har en egen, specifik metod för att först beräkna sitt CTE\-mått från tillverkarens "b-mått".  
     * CustomAngleBend har en egen metod som specificerar att den bara ska ha en tangent.  
3. **Taggning av Operation:** När en komponentklass bygger sin lista av geometriska primitiv, är den också ansvarig för att läsa build\_operation från katalogdatan och fästa den på varje primitiv den skapar.  
4. **Utbyggbarhet:** För att lägga till en ny komponenttyp (t.ex. en ventil) skapas en ny klass som innehåller den specifika beräkningslogiken och vet vilken build\_operation som ska taggas.

### **4\. Kodskelett (**factory.py**)**

Kodskelettet visar hur en "dispatcher"-metod kan skapa en instans av rätt klass baserat på nodens egenskaper.

\# backendv2/pipeline/component\_factory/factory.py  
from typing import Dict, Any, List  
\# ... andra importer

\# \--- Definition av komponentklasser \---  
class BaseComponent:  
    def \_\_init\_\_(self, node\_info, catalog\_data):  
        self.node\_info \= node\_info  
        self.catalog\_data \= catalog\_data  
        self.build\_operation \= catalog\_data.get('build\_operation', 'sweep') \# Default till sweep

    def get\_geometry(self) \-\> List\[Dict\[str, Any\]\]:  
        raise NotImplementedError

class BendComponent(BaseComponent):  
    def \_calculate\_tangent(self, cte, radius):  
        return cte \- radius  
    \# ... mer gemensam logik

\# \--- Fabriksklassen \---  
class ComponentFactory:  
    """  
    Skapar och returnerar den lokala centrumlinje-geometrin  
    för enskilda komponenter genom att instansiera rätt klass.  
    """  
    def \_\_init\_\_(self, catalog: Any):  
        self.catalog \= catalog

    def create\_component\_geometry(self, node: NodeInfo) \-\> List\[Dict\[str, Any\]\]:  
        """  
        Huvud-dispatcher som väljer och instansierar rätt komponentklass.  
        """  
        component\_class \= self.\_get\_component\_class(node)  
        if component\_class:  
            \# Hämta rådata från katalogen  
            catalog\_data \= self.catalog.get\_component\_data(...)  
            \# Skapa en instans av komponenten  
            component\_instance \= component\_class(node, catalog\_data)  
            \# Returnera dess beräknade och taggade geometri  
            return component\_instance.get\_geometry()  
        return \[\]

    def \_get\_component\_class(self, node: NodeInfo) \-\> Any:  
        """Hjälpmetod för att mappa en nod till en klass."""  
        if isinstance(node, BendNodeInfo):  
            \# ... logik för att returnera Bend90, Bend45 etc.  
            pass  
        return None

### **5\. Sammanfattning och Gränssnitt mot Nästa Modul**

Genom att isolera all komponent-specifik logik här, inklusive taggningen av 3D-operationer, uppnår vi vårt mål om ett extremt utbyggbart system. CenterlineBuilder kan sedan använda denna fabrik för att få korrekta "subassemblies" utan att behöva känna till deras interna logik.

## **Modul 5: Byggmästaren (**CenterlineBuilder**)**

### **1\. Syfte och Ansvar**

* **Syfte:** Att agera som den centrala byggmotorn i systemet. Den tar en enkel, sekventiell "resplan" och omvandlar den till en komplett, geometriskt perfekt och detaljerad bygghandling (den oändligt tunna centrumlinjen).  
* **Enskilt Ansvar:**  
  1. **Följa Planen:** Att sekventiellt stega igenom en resplan från Planner.  
  2. **Använda Fabriken:** Att för varje NODE\-steg i planen, anropa ComponentFactory för att få den korrekta, lokala geometrin för komponenten.  
  3. **Beräkna Raka Rör:** Att för varje EDGE\-steg i planen, beräkna den exakta längden på det raka rörsegment som behövs för att ansluta de två omgivande komponenterna.  
  4. **Montera Geometrin:** Att sammanfoga komponenternas geometri med de raka rörens geometri till en enda, kontinuerlig och korrekt centrumlinje.

### **2\. Dataflöde**

* **Indata:** En enskild resplan (List\[Dict\[str, str\]\]) från Planner, samt tillgång till ComponentFactory, TopologyBuilders graf och nodlista.  
* **Utdata:** En enda, komplett lista av geometriska primitiv (List\[Dict\[str, Any\]\]). Denna lista är den slutgiltiga bygghandlingen, redo att skickas till Adjuster eller GeometryExecutor.

### **3\. Design av Utdata**

Utdata är en detaljerad, "taggad" lista som GeometryExecutor kan följa blint.

\# Exempel på den detaljerade bygghandling som CenterlineBuilder producerar  
centerline\_primitives \= \[  
    \# Geometri för första komponenten (en böj)  
    {'type': 'LINE', 'length': 32.0, 'is\_tangent': True, 'build\_operation': 'sweep'},  
    {'type': 'ARC', 'radius': 38.0, 'angle': 90.0, 'build\_operation': 'sweep'},  
    {'type': 'LINE', 'length': 32.0, 'is\_tangent': True, 'build\_operation': 'sweep'},  
      
    \# Rakt rör som ansluter  
    {'type': 'LINE', 'length': 860.0, 'is\_tangent': False, 'build\_operation': 'sweep'},

    \# Geometri för nästa komponent (ett T-rör)  
    {'type': 'LINE', 'length': 51.0, 'is\_tangent': True, 'build\_operation': 'sweep'},  
    \# ... etc.  
\]

### **4\. Logiskt Flöde (En-stegs-metoden)**

Modulen använder "3D-penna"-metaforen för att sekventiellt bygga upp centrumlinjen.

1. **Initiera Pennan:** Startar en "penna" med en position och en riktning vid startpunkten för den givna resplanen.  
2. **Loopa Genom Planen:** Itererar igenom varje steg (NODE eller EDGE) i resplanen.  
   * **Om steget är** NODE**:**  
     1. Anropar ComponentFactory för att få den lokala geometrin för noden (t.ex. \[LINE, ARC, LINE\]).  
     2. För varje primitiv i den returnerade geometrin: "ritar" den (dvs. beräknar dess slutpunkt och lägger till den i den slutgiltiga listan) och uppdaterar pennans position och riktning.  
   * **Om steget är** EDGE**:**  
     1. Använder sin **två-pass-metod (Mät & Diagnos)** för att beräkna den exakta längden på det raka röret.  
     2. Om längden är negativ (överlapp), anropas Adjuster\-modulen för att få en korrigerad lösning.  
     3. "Ritar" det raka röret med den korrekta längden och uppdaterar pennans position.  
3. **Slutförande:** När loopen är klar, returneras den kompletta listan av geometriska primitiv.

### **5\. Kodskelett (**centerline\_builder.py**)**

\# backendv2/pipeline/centerline\_builder.py

class CenterlineBuilder:  
    """  
    Bygger en komplett, detaljerad centrumlinje genom att följa en resplan  
    och använda ComponentFactory.  
    """  
    def \_\_init\_\_(self, plan, nodes, topology, factory, adjuster):  
        self.plan \= plan  
        self.nodes\_by\_id \= {node.id: node for node in nodes}  
        self.topology \= topology  
        self.factory \= factory  
        self.adjuster \= adjuster  
        self.pen\_position \= ... \# Vec3  
        self.pen\_direction \= ... \# Vec3

    def build\_centerline(self) \-\> List\[Dict\[str, Any\]\]:  
        """  
        Huvudmetod som exekverar byggprocessen.  
        """  
        print(f"--- Modul 5 (CenterlineBuilder): Startar bygge av centrumlinje \---")  
        final\_primitives \= \[\]  
          
        for step in self.plan:  
            if step\['type'\] \== 'NODE':  
                node \= self.nodes\_by\_id\[step\['id'\]\]  
                component\_primitives \= self.factory.create\_component\_geometry(node)  
                \# TODO: Loopa igenom och "rita" varje primitiv, uppdatera pennan  
                final\_primitives.extend(component\_primitives)  
              
            elif step\['type'\] \== 'EDGE':  
                \# TODO: Implementera två-pass-metoden (Mät & Diagnos)  
                \# 1\. Mät avstånd mellan noderna för denna kant.  
                \# 2\. Hämta tangentkrav från föregående och nästa komponent.  
                \# 3\. Beräkna längden på det raka röret.  
                \# 4\. Om negativt, anropa self.adjuster.  
                \# 5\. "Rita" det raka röret.  
                pass  
          
        return final\_primitives

### **6\. Sammanfattning och Gränssnitt mot Nästa Modul**

CenterlineBuilder är den primära "intelligenta" byggaren. Den orkestrerar processen, konsulterar experter (ComponentFactory, Adjuster) och producerar den slutgiltiga, perfekta bygghandlingen. Nästa modul, Adjuster, kommer bara att anropas av denna modul vid behov, och GeometryExecutor kommer att ta emot dess slutgiltiga output.

## **Modul 6: Kvalitetskontrollanten (**Adjuster**)**

### **1\. Syfte och Ansvar**

* **Syfte:** Att agera som en högt specialiserad "problemlösare" som anropas av CenterlineBuilder **endast** när ett geometriskt problem uppstår som inte kan lösas lokalt.  
* **Enskilt Ansvar:** Att hantera det specifika scenariot där det totala utrymmet som krävs av en **hel kedja av komponenters** tangenter är större än det faktiska avståndet mellan två huvudnoder (ett "överlapp" eller "underskott"). Dess enda jobb är att intelligent bestämma hur dessa tangenter ska kapas för att passa, baserat på en filosofi som minimerar antalet kap.

### **2\. Dataflöde**

* **Indata:** Ett anrop från CenterlineBuilder med specifik information om problemet:  
  * En **lista** av alla komponent-noder i det problematiska segmentet.  
  * Storleken på det totala överlappet/underskottet (t.ex. \-20.0 mm).  
* **Utdata:** En dictionary som mappar varje berörd nod-ID till dess **nya, kapade geometri**. CenterlineBuilder använder sedan denna data för att bygga den korrekta centrumlinjen.

### **3\. Logiskt Flöde (Svetsarens Prioriterings-algoritm)**

Modulen efterliknar en erfaren svetsares tankeprocess för att hitta den enklaste och renaste lösningen, istället för en naiv matematisk optimering.

1. **Anrop:** CenterlineBuilder anropar adjuster.resolve\_shortfall\_for\_segment(segment\_nodes, shortfall).  
2. **Inventering:** Modulen inventerar alla kapbara tangenter i segmentet och beräknar deras "spelrum" (nuvarande längd \- fysisk minimilängd).  
3. **Prioritet 1: "En-kaps-lösning"**  
   * Algoritmen letar först efter en **enda** tangent som har tillräckligt med "spelrum" för att absorbera **hela** underskottet.  
   * Om en sådan tangent hittas, är det den optimala lösningen. Den kapade geometrin för just den komponenten beräknas och returneras.  
4. **Prioritet 2: "Få-kaps-lösning"**  
   * Om ingen en-kaps-lösning finns, försöker algoritmen hitta den **minsta gruppen** av tangenter vars kombinerade "spelrum" kan lösa underskottet.  
   * Den kan sedan fördela kapningen på ett "snyggt" sätt, t.ex. jämnt fördelat mellan de två komponenter som har mest att ge.  
5. **Resultat & Felhantering:**  
   * Om en lösning hittas, returneras en dictionary med de nya, kapade komponent-geometrierna.  
   * Om det totala spelrummet för alla tangenter i segmentet är mindre än underskottet, är designen omöjlig att bygga. Modulen kastar då ett ImpossibleBuildError.

### **4\. Kodskelett (**adjuster.py**)**

\# backendv2/pipeline/adjuster/adjuster.py

class ImpossibleBuildError(Exception):  
    pass

class Adjuster:  
    """  
    Hanterar specialfall för geometrisk justering, primärt  
    inkapning av tangenter vid platsbrist över ett helt segment.  
    """  
    def \_\_init\_\_(self, factory: 'ComponentFactory'):  
        self.factory \= factory

    def resolve\_shortfall\_for\_segment(self, segment\_nodes: List\['NodeInfo'\], shortfall: float) \-\> Dict\[str, List\[Dict\]\]:  
        """  
        Tar emot en lista av noder i ett segment och ett underskott,  
        och returnerar nya, justerade geometrier för de berörda komponenterna.  
        """  
        print(f"--- Modul 6 (Adjuster): Hanterar överlapp på {shortfall:.2f}mm \---")  
          
        \# TODO: Implementera "Svetsarens Prioriterings-algoritm".  
        \# 1\. Inventera alla kapbara tangenter och deras "spelrum".  
        \# 2\. Försök hitta en "En-kaps-lösning".  
        \# 3\. Om det misslyckas, försök hitta en "Få-kaps-lösning".  
        \# 4\. Om omöjligt, kasta ImpossibleBuildError.

        \# Exempel på returdata för en "En-kaps-lösning"  
        adjusted\_geometries \= {  
            'node\_id\_1': \[ {'type': 'LINE', 'length': 12.0, ...}, {'type': 'ARC', ...} \], \# Den enda kapade  
        }  
          
        return adjusted\_geometries

### **5\. Sammanfattning och Gränssnitt mot Nästa Modul**

Adjuster är en högt specialiserad konsult. Genom att isolera denna komplexa undantagslogik här, håller vi CenterlineBuilder ren och fokuserad på den normala byggprocessen. Detta gör systemet avsevärt mycket enklare att förstå och felsöka.

## **Modul 7: 3D-Modellbyggaren (**GeometryExecutor**)**

### **1\. Syfte och Ansvar**

* **Syfte:** Att agera som en automatiserad CAD-robotarm. Detta är den enda modulen i hela pipelinen som har ett direkt beroende till och anropar FreeCADs bibliotek.  
* **Enskilt Ansvar:** Att ta emot en perfekt, detaljerad och "taggad" bygghandling från CenterlineBuilder och blint exekvera den. Den fattar inga egna beslut, utan följer bara de instruktioner den får.

### **2\. Dataflöde**

* **Indata:** En lista av bygghandlingar (en för varje gren i rörsystemet). Varje bygghandling är en lista av geometriska primitiv (LINE, ARC) från CenterlineBuilder.  
* **Utdata:** Ett enda, slutgiltigt Part.Shape\-objekt som representerar hela den sammanslagna 3D-modellen (den digitala tvillingen).

### **3\. Logiskt Flöde**

Modulen arbetar sekventiellt och är helt frikopplad från den komplexa logiken i de tidigare stegen. Den förlitar sig på att varje segment i bygghandlingen är korrekt 'taggad' med en build\_operation (t.ex. 'sweep', 'loft'), en instruktion vars ursprung är den domänspecifika kunskapen i **Modul 4 (**ComponentFactory**)**.

1. **Fas A: Rita Centrumlinjerna:**  
   * Modulen loopar igenom varje bygghandling den har fått.  
   * För varje handling använder den en "3D-penna" för att rita ut den kompletta, oändligt tunna Part.Wire\-geometrin. Detta skapar en exakt "väg" för varje rörgren.  
2. **Fas B: Skapa Solider:**  
   * Modulen går igenom varje bygghandling och dess motsvarande, nyss skapade centrumlinje.  
   * För varje geometrisk primitiv (LINE eller ARC) i handlingen:  
     1. Den läser build\_operation\-taggen.  
     2. Den anropar en specifik hjälp-metod (\_create\_sweep\_body, \_create\_loft\_body) som applicerar rätt 3D-operation på motsvarande del av centrumlinjen.  
     3. Den resulterande 3D-kroppen sparas i en lista.  
3. **Fas C: Sammanslagning:**  
   * När alla individuella 3D-kroppar har skapats, används Part.MultiFuse eller motsvarande (inte helt fastslagit ännu) för att foga samman dem till en enda, solid och sammanhängande 3D-modell.

### **4\. Kodskelett (**executor.py**)**

\# backendv2/pipeline/geometry\_executor/executor.py  
import Part  
from FreeCAD import Vector

class GeometryExecutor:  
    """  
    Tar en slutgiltig, justerad bygghandling och skapar en 3D-modell i FreeCAD.  
    """  
    def \_\_init\_\_(self, final\_plans: List\[List\[Dict\[str, Any\]\]\], catalog: Any):  
        self.plans \= final\_plans  
        self.catalog \= catalog  
        self.solid\_bodies: List\[Part.Shape\] \= \[\]

    def build\_model(self) \-\> Part.Shape:  
        """Huvudmetod som kör hela byggprocessen i tre steg."""  
        print("--- Modul 7 (GeometryExecutor): Startar 3D-modellbygge \---")  
          
        centerline\_wires \= self.\_build\_centerlines()  
        print(f"  \-\> Fas A: {len(centerline\_wires)} centrumlinjer skapade.")  
          
        self.\_create\_solid\_bodies(centerline\_wires)  
        print(f"  \-\> Fas B: {len(self.solid\_bodies)} solida kroppar skapade.")

        final\_model \= self.\_fuse\_solids()  
        print(f"  \-\> Fas C: Sammanslagning klar.")  
          
        return final\_model

    def \_build\_centerlines(self) \-\> List\[Part.Wire\]:  
        """Loopar igenom self.plans och skapar en Part.Wire för varje."""  
        \# TODO: Implementera logik för att skapa Part.Wire från primitiv.  
        return \[\]

    def \_create\_solid\_bodies(self, centerline\_wires: List\[Part.Wire\]):  
        """Loopar igenom planer och centrumlinjer för att skapa solider."""  
        \# TODO: Implementera logik för att anropa rätt \_create\_...\_body-metod  
        \# baserat på 'build\_operation'-taggen.  
        pass

    def \_fuse\_solids(self) \-\> Part.Shape:  
        """Använder Part.MultiFuse för att slå ihop self.solid\_bodies."""  
        if not self.solid\_bodies:  
            return Part.Shape()  
        if len(self.solid\_bodies) \== 1:  
            return self.solid\_bodies\[0\]  
        return self.solid\_bodies\[0\].multiFuse(self.solid\_bodies\[1:\])

### **5\. Sammanfattning**

GeometryExecutor är den sista, "dumma" arbetaren i vår pipeline. Dess strikta separation från den komplexa beräkningslogiken gör systemet extremt testbart (eftersom alla moduler utom denna kan testas utan FreeCAD) och uppfyller vår kärnfilosofi: **Data Först, Geometri Sist**.