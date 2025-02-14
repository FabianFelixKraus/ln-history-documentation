import networkx as nx
import matplotlib.pyplot as plt
import numpy as np
from cairosvg import svg2png  
from PIL import Image
import os

def convert_png_to_ico(png_path, ico_path, sizes=[16, 32, 48, 64]):
    """Convert a PNG file to an ICO file with multiple sizes."""
    img = Image.open(png_path)
    img.save(ico_path, format="ICO", sizes=[(s, s) for s in sizes])

def create_graph(nodes=50, edge_prob=0.3, seed=None):
    """Create a random directed graph with given nodes and edge probability."""
    np.random.seed(seed)
    G = nx.gnp_random_graph(nodes, edge_prob, directed=True)
    return G

def position_nodes(a, b, c, d, n, seed=None):
    """Position 10 nodes on a polynomial curve and add 40 uniformly distributed nodes."""
    np.random.seed(seed)
    
    # Polynomial curve nodes
    x_vals = np.linspace(-1, 1, n)
    y_vals = a * x_vals**3 + b * x_vals**2 + c * x_vals + d
    highlighted_pos = {i: (x_vals[i], y_vals[i]) for i in range(n)}
    
    # Randomly placed nodes
    additional_pos = {i + n: (np.random.uniform(-1, 1), np.random.uniform(-1, 1)) for i in range(4*n)}

    # Merge both sets of positions
    pos = {**highlighted_pos, **additional_pos}
    return pos, highlighted_pos

def draw_graph(G, pos, highlighted_pos, n, size, mode="light"):
    """Draw the graph with colors adapted for light or dark mode."""
    plt.figure(figsize=(size, size))
    
    if mode == "light":
        node_color, edge_color, highlight_node, highlight_edge, bg_color = "#7b2cbf", "#7b2cbf", "#FF9900", "#FF9900", "#d3d3d3" 
    else:
        node_color, edge_color, highlight_node, highlight_edge, bg_color = "#BB86FC", "#BB86FC", "#FFD700", "#FFD700", "#121212"
    
    plt.gca().set_facecolor(bg_color)
    
    # Draw base graph nodes and edges
    nx.draw(G, pos, node_color=node_color, edge_color=edge_color, alpha=0.75, node_size=100)
    
    # Draw highlighted nodes and edges
    highlighted_path = [(i, i+1) for i in range(n-1)]
    nx.draw_networkx_nodes(range(n), highlighted_pos, node_color=highlight_node, node_size=300)
    nx.draw_networkx_edges(G, pos, edgelist=highlighted_path, edge_color=highlight_edge, width=2.5)
    
    plt.axis("off")
    
    # Save SVG
    output_dir = "./themes/DeepThought/static/icons"
    svg_filename = f"favicon_{mode}.svg"
    plt.savefig(os.path.join(output_dir, svg_filename), format="svg", facecolor=bg_color, bbox_inches='tight')
    plt.close()

    # Different browser / versions
    # Convert SVG to PNG at different resolutions
    # for size in [16, 32, 48, 150, 180, 192, 300, 384, 450]:
    for size in [16, 32, 48, 180]:
        png_filename = f"favicon_{mode}_{size}x{size}.png"
        svg2png(url=os.path.join(output_dir, svg_filename), write_to=os.path.join(output_dir, png_filename), output_width=size, output_height=size)
        print(f"Saved {png_filename}")

    # Android / Chrome
    for size in [192, 384]:
        png_filename = f"android-chrome-{size}x{size}.png"
        svg2png(url=os.path.join(output_dir, svg_filename), write_to=os.path.join(output_dir, png_filename), output_width=size, output_height=size)
        print(f"Saved {png_filename}")

    size=150
    png_filename = f"mstile-{size}x{size}.png"
    svg2png(url=os.path.join(output_dir, svg_filename), write_to=os.path.join(output_dir, png_filename), output_width=size, output_height=size)
    print(f"Saved {png_filename}")

    # standard / logo
    size = 300
    png_filename = f"logo_{size}x{size}.png"
    svg2png(url=os.path.join(output_dir, svg_filename), write_to=os.path.join("./themes/DeepThought/static/images", png_filename), output_width=size, output_height=size)
    

def main():
    G = create_graph(nodes=30, edge_prob=0.05, seed=21)
    n = 6
    pos, highlighted_pos = position_nodes(seed=21, a=2, b=0.3, c=-1.1, d=-0.2, n=n)
    
    size=4
    # draw_graph(G, pos, highlighted_pos, n, size=size, mode="light")
    draw_graph(G, pos, highlighted_pos, n, size=size, mode="dark")

    convert_png_to_ico("./themes/DeepThought/static/icons/favicon_dark_48x48.png",
                   "./themes/DeepThought/static/icons/favicon.ico")

if __name__ == "__main__":
    main()
