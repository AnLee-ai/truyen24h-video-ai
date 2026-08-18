from dulwich.repo import Repo
import os

repo = Repo('.')
commit = repo[b'25c8c70c4ba9ddae5a4c530fb4a5fb40aef59193']
tree = repo[commit.tree]

def restore_tree(repo, tree_sha, path=""):
    tree = repo[tree_sha]
    for item in tree.items():
        item_path = os.path.join(path, item.path.decode('utf-8'))
        if item.mode == 0o40000: # Directory
            restore_tree(repo, item.sha, item_path)
        else:
            if item_path.startswith('src') and item_path.endswith('.py'):
                with open(item_path, 'wb') as f:
                    f.write(repo[item.sha].data)
                print(f"Restored {item_path}")

restore_tree(repo, tree.id)
