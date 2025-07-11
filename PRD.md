# **Product Requirement Document (PRD): backendv2**

Version: 2.0  
Datum: 2025-07-09  
Ägare: Utvecklingsteam

## **1\. Projektöversikt och Vision**

### **1.1. Huvudsyfte**

Detta backend-system transformerar isometriska 2D-rörskisser till exakta, tillverkningsbara 3D-modeller. Målet är inte bara att skapa en geometrisk representation, utan en **digital tvilling** som är optimerad för den verkliga tillverkningsprocessen.

### **1.2. Affärsmål och Vision**

* **Skalbar Grund:** Skapa en stabil och skalbar backend som kan ligga till grund för en kommersiell produkt.  
* **Garanterad Byggbarhet:** Säkerställa att alla genererade 3D-modeller är "garanterat byggbara" genom att basera dem på en digital produktkatalog och beprövade tillverkningsprinciper.  
* **Konservera Branschkunskap:** Systemet ska kodifiera den tysta, erfarenhetsbaserade kunskapen som en skicklig svetsare eller ingenjör besitter. Detta är början på ett verktyg som kan fatta holistiska beslut, där den digitala tvillingen är optimerad för tillverkning, prestanda och kostnad.  
* **Möjliggöra Export:** Skapa en grund för framtida export till tekniska ritningar, STEP-filer och andra CAD-format.

## **2\. Arkitektur och Filosofi**

### **2.1. Kärnfilosofi: Data Först, Geometri Sist**

Systemet separerar strikt databearbetning från geometrisk modellering. Hela rörsystemet ska först analyseras och representeras som en komplett, intelligent och validerad datastruktur (en "bygghandling"). Först när denna datastruktur är perfekt instrueras CAD-motorn (FreeCAD) att skapa den motsvarande 3D-modellen.

### **2.2. Modulär Pipeline (7-stegsarkitekturen)**

Systemet är designat som ett digitalt, specialiserat "löpande band" i sju steg. Varje steg har ett enda, tydligt ansvar och lämnar över ett perfekt resultat till nästa.

1. **Tolkaren (SketchParser):** Läser den råa datan från 2D-ritningen och översätter den till en ren, strukturerad lista av segment.  
2. **Kartografen (TopologyBuilder):** Bygger en komplett 3D-karta (networkx-graf) av hela rörsystemet, hanterar specialgeometri och rensar bort all hjälpgometri.  
3. **Reseplaneraren (Planner):** Tar kartan och skapar en eller flera enkla, linjära "resplaner" för att hantera förgreningar och definiera byggordningen.  
4. **Komponent-specialisten (ComponentFactory):** Agerar som ett "reservdelslager". Beräknar den exakta lokala geometrin för varje enskild komponent (böjar, T-rör etc.) och taggar den med nödvändiga bygginstruktioner.  
5. **Byggmästaren (CenterlineBuilder):** Följer en resplan och använder Komponent-specialisten för att steg för steg bygga upp en komplett och perfekt, oändligt tunn centrumlinje.  
6. **Kvalitetskontrollanten (Adjuster):** En specialist som anropas av Byggmästaren **endast** vid platsbrist, för att intelligent lösa överlapp genom att kapa komponent-tangenter enligt en "svetsar-logik".  
7. **3D-Modellbyggaren (GeometryExecutor):** En "dum" CAD-robotarm som tar den perfekta centrumlinjen och blint exekverar instruktionerna för att skapa den slutgiltiga, solida 3D-modellen.

## **3\. Funktionella Krav per Modul**

### **3.1. Modul 1: SketchParser**

* **FR-1.1:** Ska kunna parsa ett protobuf-serialiserat SketchData-objekt.  
* **FR-1.2:** Ska omvandla datan till en Python-lista av dictionaries, där varje dictionary representerar ett segment.  
* **FR-1.3:** Ska för varje segment korrekt mappa och föra vidare all relevant data, inklusive (men inte begränsat till) id, start\_point, end\_point, pipeSpec, length\_dimension och isConstruction.  
* **FR-1.4:** Ska hantera frånvaron av optionella fält (som length\_dimension) utan att krascha.

### **3.2. Modul 2: TopologyBuilder**

* **FR-2.1:** Ska först bygga en komplett 2D-graf för att säkerställa att alla topologiska anslutningar är korrekta, oberoende av ritningsordning.  
* **FR-2.2:** Ska översätta den kompletta 2D-grafen till en sammanhängande 3D-graf, inklusive all hjälpgometri (konstruktionslinjer).  
* **FR-2.3:** Ska innehålla logik för att identifiera och lösa "Construction Chains" för att skapa måttlösa speciallinjer.  
* **FR-2.4:** Ska, som ett sista steg, filtrera bort **all** geometri markerad som is\_construction: true från den slutgiltiga grafen.  
* **FR-2.5:** Ska berika den slutgiltiga, rena grafens noder med typ, vinklar och rörspecifikationer.  
* **FR-2.6:** En **T-nod** (TeeNode) ska definieras som en nod med exakt **tre** anslutande kanter där isConstruction är false. Eventuella vinkel-kontroller för att identifiera "run" och "branch" ska endast utföras på dessa tre kanter.  
* **FR-2.7:** En **Hörn-nod** (BendNode) ska definieras som en nod med exakt **två** anslutande kanter där isConstruction är false, och där dessa två kanter inte är parallella med varandra.  
* **FR-2.8:** En **Ändpunkts-nod** (EndpointNode) ska definieras som en nod med exakt **en** anslutande kant där isConstruction är false.

### **3.3. Modul 3: Planner**

* **FR-3.1:** Ska kunna traversera en godtyckligt komplex, ren topologi-graf från TopologyBuilder. Traverseringen ska utgå från alla EndpointNodeInfo-noder ("utifrån och in") för att säkerställa att alla grenar i en icke-sluten topologi planeras.  
* **FR-3.2:** Ska identifiera TeeNodeInfo-noder och intelligent följa huvudflödet ("the run") för att bibehålla en logisk väg i den primära resplanen.  
* **FR-3.3:** Utdata ska vara en lista av resplaner, där varje plan är en sekvens av NODE- och EDGE-ID:n. Systemet ska garantera att varje kant i en icke-sluten topologi inkluderas i exakt en resplan.  
* **FR-3.4:** Ska ha en definierad fallback-strategi för slutna topologier (system utan ändpunkter). För V2.0 är det acceptabelt att denna strategi är att logga en varning och returnera en tom plan, då detta är ett ovanligt specialfall.

### **3.4. Modul 4: ComponentFactory**

* **FR-4.1:** Ska använda en klass-baserad struktur (t.ex. BendComponent \-\> Bend90, Bend45) för att maximera återanvändbarhet.  
* **FR-4.2:** Ska läsa rådata (t.ex. center\_to\_end) från en extern produktkatalog (JSON).  
* **FR-4.3:** Ska innehålla den matematiska logiken för att beräkna den lokala centrumlinje-geometrin (t.ex. tangentlängder) från rådatan.  
* **FR-4.4:** Ska tagga varje producerad geometrisk primitiv med en build\_operation-sträng (t.ex. "sweep", "loft") hämtad från produktkatalogen.

### **3.5. Modul 5: CenterlineBuilder**

* **FR-5.1:** Ska kunna exekvera en sekventiell resplan från Planner.  
* **FR-5.2:** Ska för varje NODE-steg anropa ComponentFactory för att hämta komponentens lokala geometri.  
* **FR-5.3:** Ska för varje EDGE-steg beräkna den nödvändiga längden för det raka rörsegmentet.  
* **FR-5.4:** Ska kunna identifiera ett geometriskt underskott (överlapp) och anropa Adjuster för att få en lösning.  
* **FR-5.5:** Utdata ska vara en komplett, "taggad" lista av geometriska primitiv.

### **3.6. Modul 6: Adjuster**

* **FR-6.1:** Ska anropas med en lista av komponenter i ett problematiskt segment samt storleken på underskottet.  
* **FR-6.2:** Ska implementera en "svetsar-logik" som prioriterar att lösa underskottet med minsta möjliga antal kap.  
* **FR-6.3:** Ska kunna kasta ett ImpossibleBuildError om underskottet inte kan lösas.  
* **FR-6.4:** Utdata ska vara de nya, justerade geometrierna för de berörda komponenterna.

### **3.7. Modul 7: GeometryExecutor**

* **FR-7.1:** Ska, i en första fas, kunna skapa en Part.Wire från en lista av geometriska primitiv.  
* **FR-7.2:** Ska, i en andra fas, kunna läsa build\_operation-taggen för varje primitiv och anropa rätt FreeCAD-operation (sweep, loft, revolve).  
* **FR-7.3:** Ska kunna slå upp rördimensioner från produktkatalogen för att skapa korrekta profiler för sweep-operationer.  
* **FR-7.4:** Ska kunna foga samman alla genererade solider till ett enda Part.Shape-objekt.

## **4\. Icke-funktionella Krav**

* **Testbarhet:** Alla moduler, med undantag för GeometryExecutor, ska kunna enhetstestas i en ren Python-miljö utan ett beroende till FreeCAD.  
* **Underhållbarhet:** Koden ska vara tydligt strukturerad i de definierade modulerna. Varje modul ska ha ett väldefinierat ansvarsområde.  
* **Prestanda:** Hela processen, från mottagen data till färdig modell, ska för ett medelstort system (ca 20-30 segment) inte överstiga 1-2 sekunder.