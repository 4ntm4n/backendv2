# **Gemini Projektkontext: backendv2**

## **1\. Projektöversikt**

* **Huvudsyfte:** Detta är ett backend-system som transformerar isometriska 2D-rörskisser till exakta, tillverkningsbara 3D-modeller. Målet är att skapa en **digital tvilling** som är optimerad för den verkliga tillverkningsprocessen.  
* **Affärsmål:** Att skapa en stabil och skalbar grund för en kommersiell produkt som **konserverar branschkunskap**. Systemet ska garantera att alla genererade modeller är geometriskt korrekta och optimerade för tillverkning, prestanda och kostnad.

## **2\. Arkitektur och Teknik**

* **Tech Stack:**  
  * Språk: Python 3.11+  
  * Frameworks: Inga specifika webb-ramverk.  
  * Databas: Ingen databas används.  
  * Viktiga bibliotek: networkx, FreeCAD (används som ett bibliotek för geometri-operationer).  
* **Arkitekturmönster:** Systemet är en **modulär pipeline i sju steg** som körs sekventiellt, baserat på principen **"Data Först, Geometri Sist"**. Se ARCHITECTURE.md för en detaljerad beskrivning.  
* **Kommunikation:** Systemet tar emot indata via ett protobuf-meddelande (SketchData) definierat i contracts/proto/sketch.proto.

## **3\. Viktiga Filer och Dokument**

### **3.1. Kod-kataloger**

* main\_runner.py: Huvudfil för att starta och orkestrera hela pipelinen.  
* pipeline/: Innehåller kärnlogiken, uppdelad enligt vår 7-stegsarkitektur.  
* contracts/: Allt som rör datakontrakt med andra system. **Ska inte ändras utan godkännande.**  
* components\_catalog/: Innehåller JSON-definitioner med **rådata** för standardkomponenter.

### **3.2. Kontext-dokument**

* ARCHITECTURE.md: **(Huvudsaklig Teknisk Plan)** Innehåller en detaljerad beskrivning av 7-stegsarkitekturen, varje moduls ansvar, dataflöden och logik.  
* PRD.md: **(Ursprungliga Krav)** Innehåller den ursprungliga Product Requirement Document med affärsmål och funktionella krav.  
* FABRICATION\_RULES.md: **(Bransch-bibeln)** Innehåller den specifika domänkunskapen om hur komponenter ska tillverkas och justeras ("svetsar-logiken").

## **4\. Kommandon och Arbetsflöden**

* **Installation:** pip install \-r requirements.txt  
* **Kör tester:** pytest eller python \-m pytest tests/  
* **Kör linter:** (Ej definierat, men ruff check . rekommenderas).  
* **Starta applikationen (via makro):** Kör BACKENDV2-RUN.FCMacro inuti FreeCAD, som i sin tur anropar main\_runner.py.

## **5\. Kodningskonventioner och Stil**

* **Formatering:** black  
* **Namngivning:** snake\_case för variabler och funktioner, PascalCase för klasser.  
* **Typning:** All ny kod ska vara fullt typ-hintad med Pythons typing-modul.

## **6\. Mål och Begränsningar**

* **Nuvarande fokus:** Att implementera den nya, robusta arkitekturen för **Modul 2: TopologyBuilder**, specifikt logiken för att först bygga en komplett 2D-graf och sedan översätta den till 3D.  
* **"No-go zones":** Ändra inte i contracts/ utan en formell överenskommelse.  
* **Antaganden:** Du kan anta att indata alltid är ett validerat SketchData protobuf-meddelande, enligt den struktur som SketchParser producerar.