from dulwich.repo import Repo
import os

repo = Repo('.')
commit = repo[b'25c8c70c4ba9ddae5a4c530fb4a5fb40aef59193']
tree = repo[commit.tree]

def restore_full_tree(repo, tree_sha, path="."):
    tree = repo[tree_sha]
    for item in tree.items():
        item_path = os.path.normpath(os.path.join(path, item.path.decode('utf-8')))
        if item.mode == 0o40000: # Directory
            if not os.path.exists(item_path):
                os.makedirs(item_path)
            restore_full_tree(repo, item.sha, item_path)
        else:
            with open(item_path, 'wb') as f:
                f.write(repo[item.sha].data)

restore_full_tree(repo, tree.id)
print("ALL FILES RESTORED FROM COMMIT 25c8c70c")
