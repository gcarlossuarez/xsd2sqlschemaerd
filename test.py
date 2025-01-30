import subprocess

test_cases = [
    "basics_type.xsd",
    "complex_types.xsd",
    "relationships.xsd",
    "choice_test.xsd",
    "circular_dependency.xsd",
    "nested_choice_test.xsd",
    "choice_example.xsd",
    "complex_types_multivalued.xsd",
]

# Python maneja mejor rutas con caracteres especiales si se usa pathlib:
from pathlib import Path
directory_path = Path(r"D:\Source\APG\COMFIAR8\Comfiar8\Documentacion\España\FacturaE\Utilitarios\VisualStudio\xsd2sqlschemaerd\tests")

for test in test_cases:
    print(f"Running test: {test}")
    file_path = directory_path / test  # Construye la ruta correctamente
    command = f'python xsd2sqlschemaerd.py "{file_path}"'
    process = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    print(process.stdout)  # Imprime el output capturado
    print(process.stderr)  # Para ver errores, si los hay

    print("-" * 50)
