#\!/usr/bin/env python3
"""
Validation Script for Neo4j Attribute Extraction Implementation
"""
import sys
import json
import traceback
from pathlib import Path
from typing import Dict, List, Any

# Add the parent directory to sys.path to import the analyzer
sys.path.insert(0, str(Path(__file__).parent.parent))

from knowledge_graphs.parse_repo_into_neo4j import Neo4jCodeAnalyzer


class AttributeExtractionValidator:
    """Validates attribute extraction against expected results"""
    
    def __init__(self):
        self.analyzer = Neo4jCodeAnalyzer()
        self.test_results = []
        self.success_count = 0
        self.failure_count = 0
        self.warning_count = 0
    
    def validate_file(self, file_path: Path, expected_results: Dict[str, Any]) -> Dict[str, Any]:
        """Validate attribute extraction for a single file"""
        print(f"
=== Validating: {file_path.name} ===")
        
        try:
            # Analyze the file
            repo_root = file_path.parent
            project_modules = {"validate_attribute_extraction"}
            analysis = self.analyzer.analyze_python_file(file_path, repo_root, project_modules)
            
            if not analysis:
                return {"status": "FAIL", "error": "No analysis returned"}
            
            # Validate each class
            validation_results = []
            for class_name, expected_attrs in expected_results.items():
                class_result = self._validate_class_attributes(
                    analysis, class_name, expected_attrs
                )
                validation_results.append(class_result)
            
            # Summarize results
            success = all(r["status"] == "PASS" for r in validation_results)
            return {
                "status": "PASS" if success else "FAIL",
                "class_results": validation_results,
                "total_classes": len(analysis["classes"]),
                "analysis_summary": {
                    "classes_found": [cls["name"] for cls in analysis["classes"]],
                    "total_attributes": sum(len(cls["attributes"]) for cls in analysis["classes"])
                }
            }
            
        except Exception as e:
            return {
                "status": "FAIL", 
                "error": str(e),
                "traceback": traceback.format_exc()
            }
    
    def _validate_class_attributes(self, analysis: Dict, class_name: str, expected_attrs: List[Dict]) -> Dict:
        """Validate attributes for a specific class"""
        # Find the class in analysis results
        target_class = None
        for cls in analysis["classes"]:
            if cls["name"] == class_name:
                target_class = cls
                break
        
        if not target_class:
            return {
                "class_name": class_name,
                "status": "FAIL",
                "error": f"Class {class_name} not found in analysis",
                "found_classes": [cls["name"] for cls in analysis["classes"]]
            }
        
        actual_attrs = target_class["attributes"]
        validation_details = []
        
        # Check each expected attribute
        for expected_attr in expected_attrs:
            attr_name = expected_attr["name"]
            found_attr = None
            
            for actual_attr in actual_attrs:
                if actual_attr["name"] == attr_name:
                    found_attr = actual_attr
                    break
            
            if not found_attr:
                validation_details.append({
                    "attribute": attr_name,
                    "status": "MISSING",
                    "expected": expected_attr,
                    "actual": None
                })
                continue
            
            # Compare attribute properties
            matches = []
            mismatches = []
            
            for prop, expected_value in expected_attr.items():
                if prop == "name":
                    continue
                    
                actual_value = found_attr.get(prop)
                if actual_value == expected_value:
                    matches.append(f"{prop}={expected_value}")
                else:
                    mismatches.append(f"{prop}: expected {expected_value}, got {actual_value}")
            
            attr_status = "PASS" if not mismatches else "PARTIAL"
            validation_details.append({
                "attribute": attr_name,
                "status": attr_status,
                "matches": matches,
                "mismatches": mismatches,
                "actual": found_attr
            })
        
        # Check for unexpected attributes
        expected_names = {attr["name"] for attr in expected_attrs}
        unexpected_attrs = [
            attr for attr in actual_attrs 
            if attr["name"] not in expected_names and not attr["name"].startswith("_")
        ]
        
        all_passed = all(detail["status"] == "PASS" for detail in validation_details)
        class_status = "PASS" if all_passed and len([d for d in validation_details if d["status"] == "MISSING"]) == 0 else "FAIL"
        
        return {
            "class_name": class_name,
            "status": class_status,
            "total_expected": len(expected_attrs),
            "total_found": len(actual_attrs),
            "validation_details": validation_details,
            "unexpected_attributes": unexpected_attrs
        }
    
    def run_validation(self):
        """Run all validation tests"""
        print("Starting Neo4j Attribute Extraction Validation")
        print("="*60)
        
        # Test cases with expected results
        test_cases = [
            {
                "file": "validate_test_dataclass_patterns.py",
                "expected": {
                    "BasicDataclass": [
                        {"name": "name", "type": "str", "is_instance": True, "from_dataclass": True, "is_class_var": False},
                        {"name": "age", "type": "int", "is_instance": True, "from_dataclass": True, "is_class_var": False},
                        {"name": "instance_count", "type": "ClassVar[int]", "is_class": True, "is_class_var": True},
                        {"name": "runtime_attr", "type": "str", "is_instance": True, "has_type_hint": False},
                        {"name": "computed_name", "is_property": True}
                    ],
                    "ComplexDataclass": [
                        {"name": "items", "type": "List[str]", "is_instance": True, "from_dataclass": True},
                        {"name": "metadata", "type": "Dict[str, int]", "is_instance": True, "from_dataclass": True},
                        {"name": "schema_version", "type": "ClassVar[str]", "is_class": True, "is_class_var": True},
                        {"name": "total_instances", "type": "ClassVar[int]", "is_class": True, "is_class_var": True},
                        {"name": "item_count", "is_property": True}
                    ],
                    "RegularClassWithClassVars": [
                        {"name": "counter", "type": "ClassVar[int]", "is_class": True, "is_class_var": True},
                        {"name": "config", "type": "ClassVar[Dict[str, str]]", "is_class": True, "is_class_var": True},
                        {"name": "name", "type": "str", "is_class": True, "is_instance": False},  # Regular class annotation
                        {"name": "instance_attr", "type": "str", "is_instance": True}
                    ]
                }
            },
            {
                "file": "validate_test_attrs_slots.py",
                "expected": {
                    "RegularClassWithSlots": [
                        {"name": "default_name", "type": "str", "is_class": True},
                        {"name": "name", "from_slots": True, "is_instance": True},
                        {"name": "value", "from_slots": True, "is_instance": True},
                        {"name": "items", "from_slots": True, "is_instance": True}
                    ],
                    "MixedPatternClass": [
                        {"name": "class_counter", "type": "int", "is_class": True},
                        {"name": "name", "type": "str", "is_class": True},  # Annotation in regular class
                        {"name": "count", "type": "int", "is_class": True},  # Annotation in regular class
                        {"name": "slot_attr", "from_slots": True, "is_instance": True},
                        {"name": "instance_created", "type": "bool", "is_instance": True},
                        {"name": "full_info", "is_property": True}
                    ]
                }
            },
            {
                "file": "validate_test_edge_cases.py",
                "expected": {
                    "DataclassEdgeCases": [
                        {"name": "union_field", "is_instance": True, "from_dataclass": True},
                        {"name": "nested_generic", "is_instance": True, "from_dataclass": True},
                        {"name": "complex_class_var", "is_class": True, "is_class_var": True},
                        {"name": "special_field", "is_instance": True, "from_dataclass": True}
                    ],
                    "PropertyOnlyClass": [
                        {"name": "read_only", "is_property": True},
                        {"name": "computed", "is_property": True}
                    ]
                }
            }
        ]
        
        # Run validation for each test case
        for test_case in test_cases:
            file_path = Path(__file__).parent / test_case["file"]
            if not file_path.exists():
                print(f"WARNING: Test file {test_case['file']} not found")
                self.warning_count += 1
                continue
                
            result = self.validate_file(file_path, test_case["expected"])
            
            if result["status"] == "PASS":
                self.success_count += 1
                print(f"✅ PASS: {test_case['file']}")
            else:
                self.failure_count += 1
                print(f"❌ FAIL: {test_case['file']}")
                if "error" in result:
                    print(f"   Error: {result['error']}")
                
                # Print detailed results for failures
                if "class_results" in result:
                    for class_result in result["class_results"]:
                        print(f"   Class {class_result['class_name']}: {class_result['status']}")
                        if class_result["status"] == "FAIL" and "validation_details" in class_result:
                            for detail in class_result["validation_details"]:
                                if detail["status"] in ["MISSING", "PARTIAL"]:
                                    print(f"      - {detail['attribute']}: {detail['status']}")
                                    if "mismatches" in detail:
                                        for mismatch in detail["mismatches"]:
                                            print(f"        {mismatch}")
            
            self.test_results.append({
                "file": test_case["file"],
                "result": result
            })
        
        # Print summary
        self._print_summary()
    
    def _print_summary(self):
        """Print validation summary"""
        print("
" + "="*60)
        print("VALIDATION SUMMARY")
        print("="*60)
        print(f"Total Tests: {self.success_count + self.failure_count}")
        print(f"Passed: {self.success_count}")
        print(f"Failed: {self.failure_count}") 
        print(f"Warnings: {self.warning_count}")
        
        if self.failure_count == 0:
            print("
🎉 ALL TESTS PASSED - Implementation ready for production\!")
            return True
        else:
            success_rate = (self.success_count / (self.success_count + self.failure_count)) * 100
            print(f"
Success Rate: {success_rate:.1f}%")
            if success_rate >= 90:
                print("✅ SUCCESS RATE > 90% - Implementation meets criteria")
                return True
            else:
                print("❌ SUCCESS RATE < 90% - Implementation needs improvement")
                return False


if __name__ == "__main__":
    validator = AttributeExtractionValidator()
    validator.run_validation()
