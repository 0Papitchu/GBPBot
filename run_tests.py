import pytest
import sys
from pathlib import Path
from datetime import datetime
import json

def run_tests():
    """Exécute tous les tests et génère un rapport"""
    test_report = {
        "date": datetime.now().isoformat(),
        "results": {}
    }
    
    # Configuration des tests
    test_paths = [
        "tests/unit",
        "tests/integration"
    ]
    
    try:
        # Exécution des tests
        for test_path in test_paths:
            print(f"\nRunning tests in {test_path}...")
            result = pytest.main(["-v", test_path])
            test_report["results"][test_path] = "PASSED" if result == 0 else "FAILED"
            
        # Sauvegarde du rapport
        report_path = Path("test_reports")
        report_path.mkdir(exist_ok=True)
        
        report_file = report_path / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, "w") as f:
            json.dump(test_report, f, indent=2)
            
        print(f"\nTest report saved to {report_file}")
        
        # Retourne le code d'erreur
        return 0 if all(r == "PASSED" for r in test_report["results"].values()) else 1
        
    except Exception as e:
        print(f"Error running tests: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(run_tests()) 