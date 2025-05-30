"""
JSON utilities for handling numpy arrays and other non-serializable types.
"""
import json
import numpy as np
from typing import Any, Dict, Union

def numpy_to_python(obj: Any) -> Any:
    """Convert numpy types to native Python types for JSON serialization."""
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, (list, tuple)):
        return [numpy_to_python(x) for x in obj]
    elif isinstance(obj, dict):
        return {k: numpy_to_python(v) for k, v in obj.items()}
    return obj

def safe_json_dumps(data: Any, **kwargs) -> str:
    """Safely serialize data to JSON, handling numpy types."""
    return json.dumps(numpy_to_python(data), **kwargs)

def safe_json_dump(data: Any, file_path: str, **kwargs) -> None:
    """Safely dump data to a JSON file, handling numpy types."""
    with open(file_path, 'w') as f:
        json.dump(numpy_to_python(data), f, **kwargs)

if __name__ == "__main__":
    # Example usage
    import numpy as np
    
    data = {
        "array": np.array([1, 2, 3]),
        "matrix": np.random.rand(2, 2),
        "int": np.int64(42),
        "float": np.float64(3.14),
        "bool": np.bool_(True),
        "nested": {
            "array": np.array([4, 5, 6])
        }
    }
    
    print(safe_json_dumps(data, indent=2))
