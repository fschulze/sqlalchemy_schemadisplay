from io import StringIO


def parse_graph(graph):
    result = {}
    graph_bytes = graph.create_plain()
    sio = StringIO(graph_bytes.decode("utf-8"))
    graph = None
    for line in sio:
        line = line.strip()
        if not line:
            continue
        if line.startswith("graph"):
            parts = line.split(None, 4)
            graph = result.setdefault(parts[1], {"nodes": {}})
            if len(parts) > 4:
                graph["options"] = parts[4]
        elif line.startswith("node"):
            parts = line.split(None, 6)
            graph["nodes"][parts[1]] = parts[6]
        elif line.startswith("edge"):
            parts = line.split(None, 3)
            graph.setdefault("edges", {})[(parts[1], parts[2])] = parts[3]
        elif line == "stop":
            graph = None
        else:
            raise ValueError("Don't know how to handle line:\n%s" % line)
    return result
