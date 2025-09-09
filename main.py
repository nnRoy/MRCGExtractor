from Repo_Graph import Repo_Graph
import argparse

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("language", type=str, help="Programming language of the repository (e.g., 'python', 'java').")
    parser.add_argument("repo_root_dir", type=str, help="Root directory of the repository to analyze.")
    parser.add_argument("out_graph_file", type=str, help="Output file path for the graph.")
    return parser.parse_args()

def main():
    args = get_args()
    repo_graph = Repo_Graph(language=args.language, repo_root_dir=args.repo_root_dir, out_graph_file=args.out_graph_file)
    repo_graph.parse_repo_graph()
    
