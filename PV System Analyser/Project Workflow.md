programma strutturato in 5 fasi**, che collega i concetti del tuo corso alla pratica con `pvlib` + `pandapower` + `networkx`.

---

## 🧩 **Obiettivo generale**

Utilizzare strumenti della **network analysis avanzata** per:

- modellare un impianto FV distribuito come grafo,
    
- studiarne la struttura, robustezza, vulnerabilità,
    
- simularne la produzione e l’impatto sulla rete,
    
- integrare nozioni teoriche (clustering, centralità, scale-free, etc.).
    

---

## 📚 **Struttura del programma in 5 fasi**

---

### ### 🔹 **Fase 1 – Modellazione del grafo (rete elettrica)**

**Obiettivi:**

- Rappresentare la rete FV come un **grafo**: bus = nodi, linee = archi.
    
- Esplorare:
    
    - **Grafi semplici, diretti, pesati**
        
    - **Bipartizione** (moduli FV vs inverter o bus MT vs BT)
        
    - **Conversione da `pandapower` a `networkx`**
        

**Strumenti:**

- `pandapower.topology.create_nxgraph(net)`
    
- `networkx.Graph` o `DiGraph`
    

**Collegamento al corso:**  
✔ Grafi semplici/diretti/pesati  
✔ Bipartizione in sottoreti FV-carico

---

### ### 🔹 **Fase 2 – Caratterizzazione topologica del network**

**Obiettivi:**

- Calcolare e visualizzare:
    
    - **Grado (connettività)**
        
    - **Centralità**: degree, closeness, betweenness
        
    - **Coefficiente di clustering**
        
    - **Diametro** e **componenti connesse**
        
    - **Cliques** e **moduli**
        

**Strumenti:**

- `networkx.degree()`, `clustering()`, `betweenness_centrality()`, `diameter()`
    
- `networkx.community` per clustering (Newman-Girvan, modularità)
    

**Collegamento al corso:**  
✔ Misure di rete locali e globali  
✔ Moduli, cluster, diametro, cliques

---

### ### 🔹 **Fase 3 – Analisi dinamica: produzione FV e flussi di potenza**

**Obiettivi:**

- Usare `pvlib` per simulare la produzione oraria dei moduli FV.
    
- Inserire generatori FV nella rete `pandapower`.
    
- Simulare il comportamento dinamico del grafo nel tempo:
    
    - variazioni di flussi,
        
    - variazioni di centralità (importanza energetica).
        

**Estensione:**

- **Grafi dinamici**: un grafo per ogni timestep o **attributi temporali** ai nodi.
    
- Analisi tipo time-series: `pandas + networkx`.
    

**Collegamento al corso:**  
✔ Serie temporali  
✔ Variazione dei parametri locali nel tempo

---

### ### 🔹 **Fase 4 – Modelli di rete e simulazioni teoriche**

**Obiettivi:**

- Confrontare la topologia reale con modelli di riferimento:
    
    - **Erdos-Renyi** (random)
        
    - **Watts-Strogatz** (small world)
        
    - **Barabasi-Albert** (scale-free)
        

**Strumenti:**

- `networkx.erdos_renyi_graph()`, `watts_strogatz_graph()`, `barabasi_albert_graph()`
    
- Calcolo distribuzioni (es. log-log del grado)
    

**Collegamento al corso:**  
✔ Reti casuali, small world, scale-free  
✔ Preferential attachment, rewiring

---

### ### 🔹 **Fase 5 – Robustezza e perturbazioni del network**

**Obiettivi:**

- Simulare **faults**: spegnimento di nodi/linee (es. guasto inverter).
    
- Misurare:
    
    - Impatto sul diametro.
        
    - Rottura della connettività.
        
    - **Efficienza** e **node relevance**.
        
- Strategie di attacco (targeted) vs errori (random).
    

**Strumenti:**

- `networkx.remove_node()`, `remove_edge()`
    
- Calcolo `efficiency`, `average_shortest_path_length`, `robustness`
    

**Collegamento al corso:**  
✔ Tolleranza ad attacchi/errori  
✔ Importanza e resilienza di nodi

---

## 🧠 **Extra opzionale – ML & node embedding**

Se arrivi fin qui, puoi:

- Estrarre **feature** dai nodi (produzione, centralità, carico).
    
- Usare **node embeddings** (Node2Vec, DeepWalk).
    
- Applicare clustering o classificazione con scikit-learn.
    

**Collegamento al corso:**  
✔ Node embedding framework  
✔ Network & ML

---

## 🔧 Vuoi iniziare da un progetto concreto?

Posso guidarti a creare una:

- rete FV di esempio (10-20 nodi),
    
- simulazione `pvlib + pandapower`,
    
- estrazione del grafo e analisi `networkx`,
    
- report con misure chiave.
    

Fammi sapere se vuoi una **base di partenza** o un **template Python** già pronto per iniziare.