# **Fabrication Rules & Domain Knowledge**

Logiken i ComponentFactory och Adjuster ska baseras på reglerna i detta dokument Detta är ett levande dokument som kommer att uppdateras eftersom, det är därför viktigt att ha en dialog med mig under utvecklingen så att vi kan synka våra förståelser för hur kunskap ska översättas till kod.

## **1\. Allmänna Principer**

* **Mål:** Minimera antalet kapningar och komplexa operationer. En lösning som kräver ett enda, enkelt kap är alltid att föredra framför en lösning som kräver flera små kap.  
* Komponenter kan ha fysiska minimått för sina tangenter. 

## **2\. Komponent-specifik Logik**

### **2.1. Böjar (Bends)**

* **Standard 90-gradersböj:**  
  * Geometrin består av \[TANGENT, ARC, TANGENT\].  
  * Tangentlängden beräknas alltid som center\_to\_end \- radius.  
* **Standard 45-gradersböj:**  
  * Geometrin består av \[TANGENT, ARC, TANGENT\].  
  * Det sanna center\_to\_end\-måttet beräknas först från tillverkarens "b-mått".  
* **Specialböj (Kapad):**  
  * Tillverkas från en standard 90-gradersböj och använder dess radie.  
  * Geometrin består av \[TANGENT, ARC\]. Den har endast en (1) full tangent.

### ***2.2. T-rör (Tees)***

* ***Placering och Grundgeometri:***  
  * *Ett T-rörs centrumlinje placeras alltid vid en `TeeNode`.*  
  * *Den består av tre tangenter: två identiska `runner`\-tangenter som utgör huvudröret, och en `branch`\-tangent som utgör avsticket.*  
  * *`Runner`\-tangenterna är parallella med varandra. `Branch`\-tangenten är alltid vinkelrät (90 grader) mot `runner`\-tangenterna.*  
* ***Dimensionering och Beräkning:***  
  * *Tangentlängderna beräknas från `center_to_end`\-mått (CTE) som finns specificerade i produktkatalogen för `RUNNER` och `BRANCH`.*  
  * *Systemet måste kunna skilja på `run`\- och `branch`\-anslutningarna på en `TeeNode` för att applicera rätt CTE-mått.*  
  * *Om `branch`\-dimensionen är mindre än `runner`\-dimensionen, kan ett reducerat T-rör användas om det finns som en standardkomponent.*  
* ***Fysiska Minimimått (Kapningsregler):***  
  * *För att undvika att geometrin för ett t-rör blir ogiltig, gäller följande minimimått för tangenter:*  
    * ***Branch-tangentens minimilängd:** `(Runner-rörets dimension / 2)`*  
    * ***Runner-tangentens minimilängd:** `(Branch-rörets dimension / 2)`*  
* *och en huvudrörstangent beskrivs: avstickstangentens dimension / 2.. Med dessa formler ser vi till att varken t-rörets avstickstangent eller någon av huvudrörstangenterna “kapar geometrin på varandra”.*   
* *Övriga noteringar om T-rör: huvudrörstangenterna är alltid paralella med varandra. Avstickstangenten är alltid perpendikulär med huvudrörstangenterna med en vinkel av exakt 90 grader.*

	

## **3\. Justeringslogik (**Adjuster**)**

### **3.1. "Svetsarens Prioriterings-algoritm" för Underskott**

När ett underskott (överlapp) uppstår i ett segment, ska följande prioriteringsordning användas för att lösa det:

1. **Prioritet 1: "En-kaps-lösning"**  
   * Sök först efter en **enda** kapbar tangent i hela segmentet som har tillräckligt med "spelrum" (nuvarande längd \- fysisk minimilängd) för att kunna absorbera **hela** underskottet.  
   * Om en sådan tangent hittas, ska **endast den** kapas. Detta är den optimala lösningen.  
2. **Prioritet 2: "Få-kaps-lösning"**  
   * Om ingen en-kaps-lösning är möjlig, hitta den **minsta möjliga gruppen** av tangenter vars kombinerade spelrum kan lösa underskottet.  
   * Fördela kapningen jämnt mellan dessa få utvalda tangenter för att skapa ett estetiskt och praktiskt resultat.  
3. **Felhantering:**  
   * Om det totala spelrummet från alla kapbara tangenter i segmentet är mindre än underskottet, är designen omöjlig att bygga. Ett ImpossibleBuildError ska kastas.