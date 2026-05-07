import os

def print_python_structure(startpath):
    print(f"Project Structure for .py files in: {os.path.abspath(startpath)}")
    print("." )
    
    for root, dirs, files in os.walk(startpath):
        # Gizli klasörleri ve sanal ortamları (venv, __pycache__) elemek için:
        dirs[:] = [d for d in dirs if not d.startswith(('.', '__')) and d not in ['venv', 'env']]
        
        # Sadece .py uzantılı dosyaları filtrele
        py_files = [f for f in files if f.endswith('.py')]
        
        # Eğer klasörde .py dosyası yoksa ve alt klasörlerinde de yoksa göstermeyebiliriz.
        # Ama basitlik adına, o anki klasörde .py varsa klasörü yazdıralım.
        if py_files:
            level = root.replace(startpath, '').count(os.sep)
            indent = ' ' * 4 * (level)
            
            # Klasör adını yazdır (root dizini değilse)
            if root != startpath:
                print(f"{indent}├── {os.path.basename(root)}/")
            
            # Dosyaları yazdır
            sub_indent = ' ' * 4 * (level + 1)
            for i, f in enumerate(py_files):
                connector = "└── " if i == len(py_files) - 1 else "├── "
                print(f"{sub_indent}{connector}{f}")

if __name__ == "__main__":
    # Scriptin çalıştığı dizini baz al
    current_directory = os.getcwd()
    print_python_structure(current_directory)