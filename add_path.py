# add_path.py
import os

def add_path_comment_to_py_files(root_dir):
    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.endswith(".py"):
                full_path = os.path.join(dirpath, filename)
                rel_path = os.path.relpath(full_path, root_dir).replace("\\", "/")

                try:
                    with open(full_path, "r", encoding="utf-8") as f:
                        lines = f.readlines()

                    # Eğer zaten ilk satır doğruysa skip
                    if lines and lines[0].strip() == f"# {rel_path}":
                        continue

                    # Eğer ilk satır yorum ama path değilse yine ekle (isteğe göre değiştirilebilir)
                    new_lines = [f"# {rel_path}\n"] + lines

                    with open(full_path, "w", encoding="utf-8") as f:
                        f.writelines(new_lines)

                    print(f"Updated: {rel_path}")

                except Exception as e:
                    print(f"Error processing {rel_path}: {e}")


if __name__ == "__main__":
    root = os.getcwd()  # scriptin çalıştığı klasör
    add_path_comment_to_py_files(root)