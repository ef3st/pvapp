from typing import List, Dict, Optional, Union
from pyvis.network import Network as PyvisNetwork
class Node:
    """Nodo base della rete (astratto)"""
    def __init__(self, id: str, **params):
        self.id = id
        self.connections: List['Node'] = []
        self.params = params

    def create_link(self, node: 'Node'):
        if node not in self.connections:
            self.connections.append(node)

    def __repr__(self):
        return f"{self.__class__.__name__}(id={self.id})"


class Modulo(Node):
    """Modulo PV"""
    def __init__(self, id: str, **params):
        super().__init__(id)


class Inverter(Node):
    """Inverter della rete"""
    def __init__(self, id: str, **params):
        super().__init__(id)


class Network:
    """Rete di pannelli e inverter"""
    def __init__(self):
        self.nodes: Dict[str, Node] = {}

    def add_node(self, node: Node):
        if node.id in self.nodes:
            raise ValueError(f"Node with id '{node.id}' already present")
        self.nodes[node.id] = node

    def link_nodes(self, id1: str, id2: str):
        if id1 not in self.nodes or id2 not in self.nodes:
            raise ValueError("Both Nodes, must be in the net")
        self.nodes[id1].create_link(self.nodes[id2])
        self.nodes[id2].create_link(self.nodes[id1])  # Connessione bidirezionale

    def get_node(self, id: str) -> Optional[Node]:
        return self.nodes.get(id)

    def __repr__(self):
        return f"Network({list(self.nodes.keys())})"

    def print_connections(self):
        for nodo in self.nodes.values():
            print(f"{nodo.id} connected to {[n.id for n in nodo.connections]}")
            
    def show_net(self) -> str:
        """Ritorna l'HTML della rete come stringa per Streamlit"""
        from pyvis.network import Network as PyvisNetwork
        import tempfile

        net_vis = PyvisNetwork(height="600px", width="100%")
        net_vis.barnes_hut()

        for nodo in self.nodes.values():
            label = f"{nodo.id}"
            title = ""
            if isinstance(nodo, Modulo):
                title = f"Modulo - W"
                color = "green"
                shape = "dot"
            elif isinstance(nodo, Inverter):
                title = f"Inverter - W"
                color = "orange"
                shape = "box"
            else:
                color = "gray"
                shape = "ellipse"

            net_vis.add_node(nodo.id, label=label, title=title, color=color, shape=shape)

        added_edges = set()
        for nodo in self.nodes.values():
            for conn in nodo.connections:
                edge = tuple(sorted((nodo.id, conn.id)))
                if edge not in added_edges:
                    net_vis.add_edge(nodo.id, conn.id)
                    added_edges.add(edge)

        # Usa un file temporaneo per salvare e leggere il contenuto HTML
        with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp_file:
            net_vis.write_html(tmp_file.name, notebook=False)

            tmp_file.seek(0)
            html_content = tmp_file.read().decode("utf-8")

        return html_content